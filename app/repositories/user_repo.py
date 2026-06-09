"""UserRepository — persistence for users."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import or_, select

from app.models.user import User
from app.repositories.base import SqlAlchemyRepository


class UserRepository(SqlAlchemyRepository[User]):
    """Data access for :class:`User`."""

    model = User

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower().strip())
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_username(self, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username.strip())
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_identifier(self, identifier: str) -> Optional[User]:
        """Look up a user by either username or email (case-insensitive email)."""
        ident = identifier.strip()
        stmt = select(User).where(
            or_(User.username == ident, User.email == ident.lower())
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def search(self, query: str, limit: int = 10) -> List[User]:
        like = f"%{query.strip()}%"
        stmt = (
            select(User)
            .where(or_(User.username.ilike(like), User.email.ilike(like)))
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())
