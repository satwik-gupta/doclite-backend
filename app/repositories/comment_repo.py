"""CommentRepository — persistence for comments, replies and suggestions."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select

from app.models.comment import Comment, CommentReply
from app.models.suggestion import Suggestion
from app.repositories.base import SqlAlchemyRepository


class CommentRepository(SqlAlchemyRepository[Comment]):
    """Data access for :class:`Comment` (plus its replies)."""

    model = Comment

    def list_for_document(self, document_id: int) -> List[Comment]:
        stmt = (
            select(Comment)
            .where(Comment.document_id == document_id)
            .order_by(Comment.created_at)
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_for_document(self, document_id: int, comment_id: int) -> Optional[Comment]:
        stmt = select(Comment).where(
            Comment.id == comment_id, Comment.document_id == document_id
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def add_reply(self, reply: CommentReply) -> CommentReply:
        self.session.add(reply)
        self.session.flush()
        return reply


class SuggestionRepository(SqlAlchemyRepository[Suggestion]):
    """Data access for :class:`Suggestion`."""

    model = Suggestion

    def list_for_document(self, document_id: int) -> List[Suggestion]:
        stmt = (
            select(Suggestion)
            .where(Suggestion.document_id == document_id)
            .order_by(Suggestion.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_for_document(
        self, document_id: int, suggestion_id: int
    ) -> Optional[Suggestion]:
        stmt = select(Suggestion).where(
            Suggestion.id == suggestion_id, Suggestion.document_id == document_id
        )
        return self.session.execute(stmt).scalar_one_or_none()
