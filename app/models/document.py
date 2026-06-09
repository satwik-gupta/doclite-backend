"""Document ORM model. Rich-text body is stored as an HTML string."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    """A rich-text document owned by a user and optionally shared with others.

    ``content_html`` holds the canonical body as sanitized HTML so that formatting
    (headings, bold/italic/underline, ordered/unordered lists) survives reload.
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled document")
    content_html: Mapped[str] = mapped_column(Text, nullable=False, default="<p></p>")
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    owner: Mapped["User"] = relationship(
        back_populates="owned_documents", foreign_keys=[owner_id]
    )
    shares: Mapped[List["DocumentShare"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    versions: Mapped[List["DocumentVersion"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.created_at",
    )
    comments: Mapped[List["Comment"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    suggestions: Mapped[List["Suggestion"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Document id={self.id} title={self.title!r} owner_id={self.owner_id}>"
