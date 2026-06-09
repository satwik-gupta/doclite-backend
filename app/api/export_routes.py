"""Export routes — stream .md / .pdf downloads (access-controlled)."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from app.api.deps import CurrentUserDep, ExportServiceDep

router = APIRouter(prefix="/api/documents", tags=["export"])


@router.get("/{document_id}/export/{fmt}")
def export_document(
    document_id: int,
    fmt: str,
    current_user: CurrentUserDep,
    exports: ExportServiceDep,
) -> Response:
    result = exports.export(current_user, document_id, fmt)
    return Response(
        content=result.content,
        media_type=result.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            # Expose the header so the browser fetch wrapper can read the filename.
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
