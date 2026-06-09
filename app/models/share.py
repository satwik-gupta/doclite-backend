"""DocumentShare ORM model — a (document, user) collaborator grant with a role."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums import Role


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DocumentShare(Base):
    """Associates a user with a document at a specific (non-owner) role.

    The owner is intentionally NOT stored here — ownership lives on
    ``Document.owner_id``. Shares cover EDITOR / COMMENTER / VIEWER grants.
    """

    __tablename__ = "document_shares"
    __table_args__ = (
        UniqueConstraint("document_id", "user_id", name="uq_share_document_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[Role] = mapped_column(
        SAEnum(Role, native_enum=False, length=20), nullable=False, default=Role.VIEWER
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    document: Mapped["Document"] = relationship(back_populates="shares")
    user: Mapped["User"] = relationship(back_populates="shares")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<DocumentShare doc={self.document_id} user={self.user_id} "
            f"role={self.role.value}>"
        )
