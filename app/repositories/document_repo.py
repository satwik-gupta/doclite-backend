"""DocumentRepository — persistence and ownership/sharing queries for documents."""
from __future__ import annotations

from typing import List

from sqlalchemy import select

from app.models.document import Document
from app.models.share import DocumentShare
from app.repositories.base import SqlAlchemyRepository


class DocumentRepository(SqlAlchemyRepository[Document]):
    """Data access for :class:`Document`."""

    model = Document

    def list_owned_by(self, user_id: int) -> List[Document]:
        stmt = (
            select(Document)
            .where(Document.owner_id == user_id)
            .order_by(Document.updated_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_shared_with(self, user_id: int) -> List[Document]:
        """Documents shared with the user (excludes ones they own)."""
        stmt = (
            select(Document)
            .join(DocumentShare, DocumentShare.document_id == Document.id)
            .where(DocumentShare.user_id == user_id)
            .where(Document.owner_id != user_id)
            .order_by(Document.updated_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())
