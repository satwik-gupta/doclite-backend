"""ShareRepository — persistence for collaborator grants."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select

from app.models.share import DocumentShare
from app.repositories.base import SqlAlchemyRepository


class ShareRepository(SqlAlchemyRepository[DocumentShare]):
    """Data access for :class:`DocumentShare`."""

    model = DocumentShare

    def get_for_user_document(
        self, document_id: int, user_id: int
    ) -> Optional[DocumentShare]:
        stmt = select(DocumentShare).where(
            DocumentShare.document_id == document_id,
            DocumentShare.user_id == user_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_for_document(self, document_id: int) -> List[DocumentShare]:
        stmt = (
            select(DocumentShare)
            .where(DocumentShare.document_id == document_id)
            .order_by(DocumentShare.created_at)
        )
        return list(self.session.execute(stmt).scalars().all())
