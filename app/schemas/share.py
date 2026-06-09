"""Sharing schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.enums import Role


class ShareCreate(BaseModel):
    """Grant or update access for a known user, by username or email."""

    identifier: str = Field(min_length=1, max_length=255, description="username or email")
    role: Role = Field(description="editor | commenter | viewer")


class RoleUpdate(BaseModel):
    role: Role
