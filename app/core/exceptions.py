"""Custom exception hierarchy and centralized FastAPI handlers.

All domain/service errors derive from ``DocLiteError``. Each carries an HTTP status
code and a stable machine-readable ``code``. A single registered handler converts
them into the structured envelope ``{"error": {"code", "message"}}`` so stack traces
never leak to clients.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class DocLiteError(Exception):
    """Base class for all application errors."""

    status_code: int = 400
    code: str = "doclite_error"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.__class__.__doc__ or "DocLite error"
        super().__init__(self.message)


class NotFoundError(DocLiteError):
    """The requested resource does not exist."""

    status_code = 404
    code = "not_found"


class PermissionDeniedError(DocLiteError):
    """The current user is not allowed to perform this action."""

    status_code = 403
    code = "permission_denied"


class AuthenticationError(DocLiteError):
    """Authentication failed or credentials are missing/invalid."""

    status_code = 401
    code = "authentication_error"


class ValidationError(DocLiteError):
    """The supplied input is invalid."""

    status_code = 422
    code = "validation_error"


class UnsupportedFileTypeError(DocLiteError):
    """The uploaded file type is not supported."""

    status_code = 415
    code = "unsupported_file_type"


class ConflictError(DocLiteError):
    """The request conflicts with current server state."""

    status_code = 409
    code = "conflict"


def _envelope(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach centralized handlers to the FastAPI application."""

    @app.exception_handler(DocLiteError)
    async def _handle_doclite_error(_: Request, exc: DocLiteError) -> JSONResponse:
        return _envelope(exc.code, exc.message, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Compact, non-leaking summary of pydantic validation issues.
        details = "; ".join(
            f"{'.'.join(str(p) for p in err.get('loc', []))}: {err.get('msg')}"
            for err in exc.errors()
        )
        return _envelope("validation_error", details or "Invalid request.", 422)

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "HTTP error"
        return _envelope("http_error", detail, exc.status_code)

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        # Never leak internals; log server-side in a real deployment.
        return _envelope("internal_error", "An unexpected error occurred.", 500)
