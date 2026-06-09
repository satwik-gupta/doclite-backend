"""Database engine, session factory and the declarative ``Base``.

A small `Database` class encapsulates engine/session construction so the rest of
the app depends on an object rather than module-level globals. A module-level
default instance (`db`) is provided as the composition-root wiring.
"""
from __future__ import annotations

from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings, get_settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model class."""


class Database:
    """Owns the SQLAlchemy engine and session factory for one database URL."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        connect_args = {}
        if settings.database_url.startswith("sqlite"):
            # Needed because FastAPI may touch a session across threads.
            connect_args = {"check_same_thread": False}
        self.engine = create_engine(
            settings.database_url,
            echo=settings.debug,
            future=True,
            connect_args=connect_args,
        )
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            class_=Session,
        )

    def create_all(self) -> None:
        """Create all tables. Import models so they register on ``Base.metadata``."""
        from app import models  # noqa: F401  (side-effect import registers mappers)

        Base.metadata.create_all(bind=self.engine)

    def session_scope(self) -> Iterator[Session]:
        """Yield a session, committing on success and rolling back on error."""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Composition-root default instance used by the FastAPI app and seeding script.
db = Database(get_settings())


def get_db() -> Iterator[Session]:
    """FastAPI dependency that provides a transactional session per request."""
    yield from db.session_scope()
