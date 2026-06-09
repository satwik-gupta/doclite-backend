"""Suggestion ORM model — a proposed change that never mutates the body until accepted."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums import SuggestionStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Suggestion(Base):
    """A proposed full-body replacement, stored separately from the canonical body.

    Keeping the entire proposed HTML (``proposed_html``) is a deliberately simple,
    *correct* model: accepting a suggestion replaces the document body and records a
    version; rejecting discards it. The canonical ``Document.content_html`` is never
    touched while a suggestion is ``PENDING``.
    """

    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id"), nullable=False, index=True
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    summary: Mapped[str] = mapped_column(String(255), nullable=False, default="Proposed change")
    base_html: Mapped[str] = mapped_column(Text, nullable=False)       # body when proposed
    proposed_html: Mapped[str] = mapped_column(Text, nullable=False)   # the suggested body
    status: Mapped[SuggestionStatus] = mapped_column(
        SAEnum(SuggestionStatus, native_enum=False, length=20),
        nullable=False,
        default=SuggestionStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    document: Mapped["Document"] = relationship(back_populates="suggestions")
    author: Mapped["User"] = relationship(foreign_keys=[author_id])
    resolved_by: Mapped["User"] = relationship(foreign_keys=[resolved_by_id])

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Suggestion id={self.id} doc={self.document_id} "
            f"status={self.status.value}>"
        )
