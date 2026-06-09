"""User-facing schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserPublic(BaseModel):
    """Public projection of a user (never includes the password hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    display_name: str
    created_at: datetime


class UserSummary(BaseModel):
    """Compact user reference used inside other payloads."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
