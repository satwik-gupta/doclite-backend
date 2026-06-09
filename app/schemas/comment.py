"""Comment + reply schemas."""
from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.user import UserSummary


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    anchor_start: int = Field(ge=0)
    anchor_end: int = Field(ge=0)
    quoted_text: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def _check_range(self) -> "CommentCreate":
        if self.anchor_end < self.anchor_start:
            raise ValueError("anchor_end must be >= anchor_start")
        return self


class ReplyCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class ReplyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    body: str
    author: UserSummary
    created_at: datetime


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    body: str
    author: UserSummary
    anchor_start: int
    anchor_end: int
    quoted_text: str
    resolved: bool
    created_at: datetime
    replies: List[ReplyOut] = []
