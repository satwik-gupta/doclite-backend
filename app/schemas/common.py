"""Shared / misc schemas."""
from __future__ import annotations

from pydantic import BaseModel


class MessageResponse(BaseModel):
    """Generic success envelope for actions without a richer payload."""

    message: str
