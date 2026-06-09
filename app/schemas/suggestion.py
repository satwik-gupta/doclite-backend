"""Suggestion schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import SuggestionStatus
from app.schemas.user import UserSummary


class SuggestionCreate(BaseModel):
    summary: str = Field(default="Proposed change", min_length=1, max_length=255)
    proposed_html: str = Field(min_length=1, max_length=2_000_000)


class SuggestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    summary: str
    status: SuggestionStatus
    base_html: str
    proposed_html: str
    author: UserSummary
    created_at: datetime
    resolved_at: Optional[datetime] = None
