"""Document schemas, including the per-user role projection."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import Role
from app.schemas.user import UserSummary


class DocumentCreate(BaseModel):
    title: str = Field(default="Untitled document", min_length=1, max_length=255)
    content_html: Optional[str] = Field(default=None, max_length=2_000_000)


class DocumentRename(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class DocumentUpdate(BaseModel):
    """Body save. ``create_version`` controls whether a snapshot is taken."""

    content_html: str = Field(max_length=2_000_000)
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    create_version: bool = True


class CollaboratorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: UserSummary
    role: Role


class DocumentSummary(BaseModel):
    """List-view projection; ``my_role`` is the requesting user's effective role."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    owner: UserSummary
    my_role: Role
    is_owner: bool
    updated_at: datetime
    created_at: datetime


class DocumentDetail(DocumentSummary):
    content_html: str
    collaborators: List[CollaboratorOut] = []


class DocumentListResponse(BaseModel):
    owned: List[DocumentSummary]
    shared: List[DocumentSummary]
