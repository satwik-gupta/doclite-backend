"""Abstract repository contract + a SQLAlchemy implementation base.

Services depend on the abstract :class:`AbstractRepository` interface, not on
SQLAlchemy directly (Dependency Inversion). Concrete repositories extend
:class:`SqlAlchemyRepository`, which provides generic CRUD so each concrete class
only adds aggregate-specific queries (Single Responsibility / DRY).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class AbstractRepository(ABC, Generic[ModelT]):
    """The persistence contract every repository honors (Interface Segregation)."""

    @abstractmethod
    def add(self, entity: ModelT) -> ModelT:
        """Persist a new entity and return it (with generated id)."""

    @abstractmethod
    def get(self, entity_id: int) -> Optional[ModelT]:
        """Return an entity by primary key, or ``None``."""

    @abstractmethod
    def list(self) -> List[ModelT]:
        """Return all entities of this type."""

    @abstractmethod
    def delete(self, entity: ModelT) -> None:
        """Remove an entity."""


class SqlAlchemyRepository(AbstractRepository[ModelT]):
    """Generic SQLAlchemy-backed repository. Subclasses set ``model``."""

    model: Type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        self.session.flush()  # assign PKs without ending the request transaction
        return entity

    def get(self, entity_id: int) -> Optional[ModelT]:
        return self.session.get(self.model, entity_id)

    def list(self) -> List[ModelT]:
        return list(self.session.execute(select(self.model)).scalars().all())

    def delete(self, entity: ModelT) -> None:
        self.session.delete(entity)
        self.session.flush()
