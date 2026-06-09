"""VersionService — list, fetch and non-destructively restore version snapshots.

Snapshots are created at save time by :class:`DocumentService`. Restoring a prior
version does NOT delete history: it re-saves the document body to the old content,
which appends a brand-new version labelled ``restore from vN``.
"""
from __future__ import annotations

from typing import List

from app.core.exceptions import NotFoundError
from app.domain.enums import Action
from app.models.user import User
from app.models.version import DocumentVersion
from app.repositories.version_repo import VersionRepository
from app.services.access import AccessGuard
from app.services.document_service import DocumentService, DocumentWithRole


class VersionService:
    def __init__(
        self,
        version_repo: VersionRepository,
        document_service: DocumentService,
        access: AccessGuard,
    ) -> None:
        self._versions = version_repo
        self._documents = document_service
        self._access = access

    def list_versions(self, user: User, document_id: int) -> List[DocumentVersion]:
        # Anyone who can view the document can view its history.
        self._access.require(user, document_id, Action.VIEW)
        return self._versions.list_for_document(document_id)

    def get_version(
        self, user: User, document_id: int, version_id: int
    ) -> DocumentVersion:
        self._access.require(user, document_id, Action.VIEW)
        version = self._versions.get_for_document(document_id, version_id)
        if version is None:
            raise NotFoundError("Version not found.")
        return version

    def restore_version(
        self, user: User, document_id: int, version_id: int
    ) -> DocumentWithRole:
        # Restoring is a body change -> RESTORE_VERSION capability (owner/editor).
        self._access.require(user, document_id, Action.RESTORE_VERSION)
        version = self._versions.get_for_document(document_id, version_id)
        if version is None:
            raise NotFoundError("Version not found.")
        # save_body appends a NEW snapshot, preserving the entire history.
        return self._documents.save_body(
            user,
            document_id,
            version.content_html,
            title=version.title,
            create_version=True,
            label=f"restore from v{version.version_number}",
        )
