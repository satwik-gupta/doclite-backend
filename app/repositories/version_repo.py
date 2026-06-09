"""VersionRepository — persistence for document version snapshots."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func, select

from app.models.version import DocumentVersion
from app.repositories.base import SqlAlchemyRepository


class VersionRepository(SqlAlchemyRepository[DocumentVersion]):
    """Data access for :class:`DocumentVersion`."""

    model = DocumentVersion

    def list_for_document(self, document_id: int) -> List[DocumentVersion]:
        stmt = (
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_for_document(
        self, document_id: int, version_id: int
    ) -> Optional[DocumentVersion]:
        stmt = select(DocumentVersion).where(
            DocumentVersion.id == version_id,
            DocumentVersion.document_id == document_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def next_version_number(self, document_id: int) -> int:
        stmt = select(func.coalesce(func.max(DocumentVersion.version_number), 0)).where(
            DocumentVersion.document_id == document_id
        )
        current_max = self.session.execute(stmt).scalar_one()
        return int(current_max) + 1
