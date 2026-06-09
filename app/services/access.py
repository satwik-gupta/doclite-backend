"""AccessGuard — the single load-and-authorize chokepoint for documents.

Every service that touches a document routes through :class:`AccessGuard.require`,
which (1) loads the document or raises ``NotFoundError`` and (2) asks the central
:class:`PermissionPolicy` whether the user may perform the action. This guarantees
"no scattered, duplicated permission checks" (Section 5.2): authorization logic
exists only in :class:`PermissionPolicy`, invoked only here.
"""
from __future__ import annotations

from typing import Optional, Tuple

from app.core.exceptions import NotFoundError
from app.domain.enums import Action, Role
from app.domain.policy import PermissionPolicy
from app.models.document import Document
from app.models.user import User
from app.repositories.document_repo import DocumentRepository
from app.repositories.share_repo import ShareRepository


class AccessGuard:
    """Loads documents and enforces access via the central policy."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        share_repo: ShareRepository,
        policy: PermissionPolicy,
    ) -> None:
        self._documents = document_repo
        self._shares = share_repo
        self._policy = policy

    def load(self, document_id: int) -> Document:
        document = self._documents.get(document_id)
        if document is None:
            raise NotFoundError("Document not found.")
        return document

    def share_role(self, user: User, document: Document) -> Optional[Role]:
        """The user's stored share role on the document, if any."""
        share = self._shares.get_for_user_document(document.id, user.id)
        return share.role if share else None

    def effective_role(self, user: User, document: Document) -> Optional[Role]:
        """Owner-or-share effective role (``None`` if no relationship)."""
        return self._policy.effective_role(user, document, self.share_role(user, document))

    def require(
        self, user: User, document_id: int, action: Action
    ) -> Tuple[Document, Role]:
        """Load the document and authorize ``action`` for ``user``.

        Returns ``(document, effective_role)`` or raises ``NotFoundError`` /
        ``PermissionDeniedError`` from the policy.
        """
        document = self.load(document_id)
        share_role = self.share_role(user, document)
        role = self._policy.authorize(user, action, document, share_role)
        return document, role
