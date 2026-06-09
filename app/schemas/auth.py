"""Authentication schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.user import UserPublic


class LoginRequest(BaseModel):
    """Login by username OR email + password."""

    identifier: str = Field(min_length=1, max_length=255, description="username or email")
    password: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
