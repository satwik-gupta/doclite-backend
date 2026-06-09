"""Comment + CommentReply ORM models, anchored to a text range in the document."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Comment(Base):
    """A comment anchored to a text range.

    The anchor is stored as character offsets into the document's plain-text
    projection (``anchor_start`` / ``anchor_end``) plus the ``quoted_text`` that was
    selected, so the UI can re-highlight the range and degrade gracefully if the
    body shifted.
    """

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id"), nullable=False, index=True
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    anchor_start: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    anchor_end: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quoted_text: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    document: Mapped["Document"] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship()
    replies: Mapped[List["CommentReply"]] = relationship(
        back_populates="comment",
        cascade="all, delete-orphan",
        order_by="CommentReply.created_at",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Comment id={self.id} doc={self.document_id} resolved={self.resolved}>"


class CommentReply(Base):
    """A threaded reply on a comment."""

    __tablename__ = "comment_replies"

    id: Mapped[int] = mapped_column(primary_key=True)
    comment_id: Mapped[int] = mapped_column(
        ForeignKey("comments.id"), nullable=False, index=True
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    comment: Mapped["Comment"] = relationship(back_populates="replies")
    author: Mapped["User"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CommentReply id={self.id} comment={self.comment_id}>"
