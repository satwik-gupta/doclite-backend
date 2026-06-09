"""File-import route: upload a .txt/.md/.docx and get a new editable document."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, File, UploadFile, status

from app.api.deps import (
    CurrentUserDep,
    ImportServiceDep,
    SharingServiceDep,
)
from app.api.presenters import to_detail
from app.schemas.document import DocumentDetail

router = APIRouter(prefix="/api/documents", tags=["import"])


@router.get("/import/supported-types", response_model=List[str])
def supported_types(imports: ImportServiceDep) -> List[str]:
    """The file extensions the importer accepts (shown in the UI)."""
    return imports.supported_extensions()


@router.post("/import", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED)
async def import_document(
    current_user: CurrentUserDep,
    imports: ImportServiceDep,
    sharing: SharingServiceDep,
    file: UploadFile = File(...),
) -> DocumentDetail:
    data = await file.read()
    item = imports.import_upload(current_user, file.filename or "", data)
    collaborators = sharing.list_collaborators(current_user, item.document.id)
    return to_detail(item, collaborators)
