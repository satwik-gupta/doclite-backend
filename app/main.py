"""Application factory / composition root.

``create_app`` wires middleware, the centralized exception handlers and the routers.
Routers are added phase by phase. In a combined deployment the built React bundle is
served from ``frontend/dist`` (mounted last so it never shadows ``/api`` routes).
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import (
    auth_routes,
    comment_routes,
    document_routes,
    export_routes,
    import_routes,
    share_routes,
    user_routes,
    version_routes,
    ws_routes,
)
from app.core.config import Settings, get_settings
from app.core.database import db
from app.core.exceptions import register_exception_handlers


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="DocLite — lightweight collaborative document editor.",
    )

    # CORS. Same-origin (combined image) is unaffected. For a split deploy
    # (frontend on Vercel, backend on Northflank) the explicit origin list plus the
    # `*.vercel.app` regex allow the browser app to call this API cross-origin.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

    register_exception_handlers(app)

    # --- API routers (extended in later phases) ---
    app.include_router(auth_routes.router)
    app.include_router(document_routes.router)
    app.include_router(import_routes.router)
    app.include_router(version_routes.router)
    app.include_router(export_routes.router)
    app.include_router(comment_routes.router)
    app.include_router(share_routes.router)
    app.include_router(user_routes.router)
    app.include_router(ws_routes.router)

    @app.get("/api/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "app": settings.app_name}

    @app.on_event("startup")
    def _startup() -> None:
        db.create_all()
        if settings.seed_on_startup:
            from app.seed import seed

            seed(settings, db)

    _mount_frontend(app)
    return app


def _mount_frontend(app: FastAPI) -> None:
    """Serve the built SPA if present (combined deployment)."""
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dist = os.path.join(here, "frontend", "dist")
    if not os.path.isdir(dist):
        return

    assets_dir = os.path.join(dist, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        # Unknown API/WS paths must not be masked by the SPA fallback.
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            return JSONResponse(
                status_code=404,
                content={"error": {"code": "not_found", "message": "Not found."}},
            )
        candidate = os.path.join(dist, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(dist, "index.html"))


# Module-level app for `uvicorn app.main:app`.
app = create_app()
