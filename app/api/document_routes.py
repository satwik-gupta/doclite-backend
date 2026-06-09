"""Document CRUD / rename / save / load routes (thin controllers).

Each handler delegates to a service; the service authorizes via the central policy.
Routers contain no business rules and no permission logic of their own.
"""
from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import (
    ConnectionManagerDep,
    CurrentUserDep,
    DocumentServiceDep,
    SharingServiceDep,
)
from app.api.presenters import to_detail, to_summary
from app.schemas.common import MessageResponse
from app.schemas.document import (
    DocumentCreate,
    DocumentDetail,
    DocumentListResponse,
    DocumentRename,
    DocumentUpdate,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=DocumentListResponse)
def list_documents(
    current_user: CurrentUserDep, documents: DocumentServiceDep
) -> DocumentListResponse:
    bundle = documents.list_for_user(current_user)
    return DocumentListResponse(
        owned=[to_summary(d) for d in bundle.owned],
        shared=[to_summary(d) for d in bundle.shared],
    )


@router.post("", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: DocumentCreate,
    current_user: CurrentUserDep,
    documents: DocumentServiceDep,
    sharing: SharingServiceDep,
) -> DocumentDetail:
    item = documents.create(current_user, payload.title, payload.content_html)
    collaborators = sharing.list_collaborators(current_user, item.document.id)
    return to_detail(item, collaborators)


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: int,
    current_user: CurrentUserDep,
    documents: DocumentServiceDep,
    sharing: SharingServiceDep,
) -> DocumentDetail:
    item = documents.get(current_user, document_id)
    collaborators = sharing.list_collaborators(current_user, document_id)
    return to_detail(item, collaborators)


@router.patch("/{document_id}/title", response_model=DocumentDetail)
def rename_document(
    document_id: int,
    payload: DocumentRename,
    current_user: CurrentUserDep,
    documents: DocumentServiceDep,
    sharing: SharingServiceDep,
) -> DocumentDetail:
    item = documents.rename(current_user, document_id, payload.title)
    collaborators = sharing.list_collaborators(current_user, document_id)
    return to_detail(item, collaborators)


@router.put("/{document_id}", response_model=DocumentDetail)
async def save_document(
    document_id: int,
    payload: DocumentUpdate,
    current_user: CurrentUserDep,
    documents: DocumentServiceDep,
    sharing: SharingServiceDep,
    connections: ConnectionManagerDep,
) -> DocumentDetail:
    item = documents.save_body(
        current_user,
        document_id,
        payload.content_html,
        title=payload.title,
        create_version=payload.create_version,
    )
    collaborators = sharing.list_collaborators(current_user, document_id)
    # Notify other present users that a newer version exists (live signal).
    await connections.notify_document_updated(document_id, current_user, label="save")
    return to_detail(item, collaborators)


@router.delete("/{document_id}", response_model=MessageResponse)
def delete_document(
    document_id: int,
    current_user: CurrentUserDep,
    documents: DocumentServiceDep,
) -> MessageResponse:
    documents.delete(current_user, document_id)
    return MessageResponse(message="Document deleted.")
