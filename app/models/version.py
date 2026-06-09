"""DocumentVersion ORM model — an immutable rich-text snapshot."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DocumentVersion(Base):
    """A point-in-time snapshot of a document's title + HTML body.

    Versions are append-only; restoring a prior version creates a NEW version
    rather than destroying history.
    """

    __tablename__ = "document_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_html: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False, default="save")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    document: Mapped["Document"] = relationship(back_populates="versions")
    author: Mapped["User"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<DocumentVersion doc={self.document_id} v={self.version_number} "
            f"label={self.label!r}>"
        )
