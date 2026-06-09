"""Role-based sharing routes (thin controllers)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, SharingServiceDep
from app.schemas.common import MessageResponse
from app.schemas.document import CollaboratorOut
from app.schemas.share import RoleUpdate, ShareCreate
from app.schemas.user import UserSummary

router = APIRouter(prefix="/api/documents", tags=["sharing"])


def _as_collaborator_out(collaborator) -> CollaboratorOut:
    return CollaboratorOut(
        user=UserSummary.model_validate(collaborator.user), role=collaborator.role
    )


@router.get("/{document_id}/collaborators", response_model=List[CollaboratorOut])
def list_collaborators(
    document_id: int, current_user: CurrentUserDep, sharing: SharingServiceDep
) -> List[CollaboratorOut]:
    collaborators = sharing.list_collaborators(current_user, document_id)
    return [_as_collaborator_out(c) for c in collaborators]


@router.post("/{document_id}/shares", response_model=CollaboratorOut)
def share_document(
    document_id: int,
    payload: ShareCreate,
    current_user: CurrentUserDep,
    sharing: SharingServiceDep,
) -> CollaboratorOut:
    collaborator = sharing.share(
        current_user, document_id, payload.identifier, payload.role
    )
    return _as_collaborator_out(collaborator)


@router.patch("/{document_id}/shares/{user_id}", response_model=CollaboratorOut)
def change_role(
    document_id: int,
    user_id: int,
    payload: RoleUpdate,
    current_user: CurrentUserDep,
    sharing: SharingServiceDep,
) -> CollaboratorOut:
    collaborator = sharing.change_role(current_user, document_id, user_id, payload.role)
    return _as_collaborator_out(collaborator)


@router.delete("/{document_id}/shares/{user_id}", response_model=MessageResponse)
def revoke_share(
    document_id: int,
    user_id: int,
    current_user: CurrentUserDep,
    sharing: SharingServiceDep,
) -> MessageResponse:
    sharing.revoke(current_user, document_id, user_id)
    return MessageResponse(message="Access revoked.")
