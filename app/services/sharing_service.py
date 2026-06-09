"""SharingService — grant/change/revoke collaborator roles, list collaborators.

Only the owner (per the central policy's MANAGE_SHARING capability) may manage
sharing. Ownership is implicit on the document, so a share can never carry the OWNER
role, and an owner cannot be added as their own collaborator.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.enums import Action, Role
from app.models.document import Document
from app.models.share import DocumentShare
from app.models.user import User
from app.repositories.share_repo import ShareRepository
from app.repositories.user_repo import UserRepository
from app.services.access import AccessGuard


@dataclass
class Collaborator:
    """A user + their role on a document (owner included, as OWNER)."""

    user: User
    role: Role


class SharingService:
    def __init__(
        self,
        share_repo: ShareRepository,
        user_repo: UserRepository,
        access: AccessGuard,
    ) -> None:
        self._shares = share_repo
        self._users = user_repo
        self._access = access

    def list_collaborators(self, user: User, document_id: int) -> List[Collaborator]:
        document, _ = self._access.require(user, document_id, Action.VIEW)
        result: List[Collaborator] = [Collaborator(document.owner, Role.OWNER)]
        for share in self._shares.list_for_document(document.id):
            result.append(Collaborator(share.user, share.role))
        return result

    def share(
        self, owner: User, document_id: int, identifier: str, role: Role
    ) -> Collaborator:
        document, _ = self._access.require(owner, document_id, Action.MANAGE_SHARING)
        self._reject_owner_role(role)
        target = self._resolve_target(identifier)

        if target.id == document.owner_id:
            raise ValidationError("The owner already has full access to this document.")

        existing = self._shares.get_for_user_document(document.id, target.id)
        if existing:
            existing.role = role
            return Collaborator(target, role)

        share = DocumentShare(document_id=document.id, user_id=target.id, role=role)
        self._shares.add(share)
        return Collaborator(target, role)

    def change_role(
        self, owner: User, document_id: int, target_user_id: int, role: Role
    ) -> Collaborator:
        document, _ = self._access.require(owner, document_id, Action.MANAGE_SHARING)
        self._reject_owner_role(role)
        share = self._shares.get_for_user_document(document.id, target_user_id)
        if share is None:
            raise NotFoundError("That user is not a collaborator on this document.")
        share.role = role
        return Collaborator(share.user, role)

    def revoke(self, owner: User, document_id: int, target_user_id: int) -> None:
        document, _ = self._access.require(owner, document_id, Action.MANAGE_SHARING)
        share = self._shares.get_for_user_document(document.id, target_user_id)
        if share is None:
            raise NotFoundError("That user is not a collaborator on this document.")
        self._shares.delete(share)

    # ---- helpers -------------------------------------------------------------

    @staticmethod
    def _reject_owner_role(role: Role) -> None:
        if role == Role.OWNER:
            raise ValidationError(
                "Ownership cannot be granted via sharing; choose editor, commenter or viewer."
            )

    def _resolve_target(self, identifier: str) -> User:
        target: Optional[User] = self._users.get_by_identifier(identifier)
        if target is None:
            raise NotFoundError(f"No user found matching '{identifier}'.")
        return target
