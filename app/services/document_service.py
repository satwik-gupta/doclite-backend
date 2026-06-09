"""DocumentService — create/read/rename/save/delete + owned-vs-shared listing.

All mutating operations authorize through :class:`AccessGuard` (which consults the
central policy). Saving the body optionally records a version snapshot so history is
captured at the point of the save (Section 4.7).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.core.html_sanitizer import sanitize_html
from app.domain.enums import Action, Role
from app.models.document import Document
from app.models.user import User
from app.models.version import DocumentVersion
from app.repositories.document_repo import DocumentRepository
from app.repositories.version_repo import VersionRepository
from app.services.access import AccessGuard


@dataclass
class DocumentWithRole:
    """A document paired with the requesting user's effective role."""

    document: Document
    role: Role

    @property
    def is_owner(self) -> bool:
        return self.role == Role.OWNER


@dataclass
class UserDocuments:
    owned: List[DocumentWithRole]
    shared: List[DocumentWithRole]


class DocumentService:
    """Use-cases for document lifecycle."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        version_repo: VersionRepository,
        access: AccessGuard,
    ) -> None:
        self._documents = document_repo
        self._versions = version_repo
        self._access = access

    # ---- reads ---------------------------------------------------------------

    def get(self, user: User, document_id: int) -> DocumentWithRole:
        document, role = self._access.require(user, document_id, Action.VIEW)
        return DocumentWithRole(document, role)

    def list_for_user(self, user: User) -> UserDocuments:
        owned = [DocumentWithRole(d, Role.OWNER) for d in self._documents.list_owned_by(user.id)]
        shared = []
        for doc in self._documents.list_shared_with(user.id):
            role = self._access.effective_role(user, doc)
            if role is not None:
                shared.append(DocumentWithRole(doc, role))
        return UserDocuments(owned=owned, shared=shared)

    # ---- writes --------------------------------------------------------------

    def create(
        self, owner: User, title: str, content_html: Optional[str] = None
    ) -> DocumentWithRole:
        document = Document(
            title=title.strip() or "Untitled document",
            content_html=sanitize_html(content_html or "<p></p>"),
            owner_id=owner.id,
        )
        self._documents.add(document)
        self._snapshot(document, owner, label="created")
        return DocumentWithRole(document, Role.OWNER)

    def rename(self, user: User, document_id: int, title: str) -> DocumentWithRole:
        document, role = self._access.require(user, document_id, Action.RENAME)
        document.title = title.strip() or document.title
        return DocumentWithRole(document, role)

    def save_body(
        self,
        user: User,
        document_id: int,
        content_html: str,
        title: Optional[str] = None,
        create_version: bool = True,
        label: str = "save",
    ) -> DocumentWithRole:
        document, role = self._access.require(user, document_id, Action.EDIT_BODY)
        document.content_html = sanitize_html(content_html)
        if title is not None and title.strip():
            # EDIT_BODY already grants editors title changes during a save.
            document.title = title.strip()
        if create_version:
            self._snapshot(document, user, label=label)
        return DocumentWithRole(document, role)

    def delete(self, user: User, document_id: int) -> None:
        document, _ = self._access.require(user, document_id, Action.DELETE)
        self._documents.delete(document)

    # ---- helpers -------------------------------------------------------------

    def _snapshot(self, document: Document, author: User, label: str) -> DocumentVersion:
        version = DocumentVersion(
            document_id=document.id,
            version_number=self._versions.next_version_number(document.id),
            title=document.title,
            content_html=document.content_html,
            author_id=author.id,
            label=label,
        )
        return self._versions.add(version)

    def collaborator_role(self, user: User, document: Document) -> Optional[Role]:
        return self._access.effective_role(user, document)
