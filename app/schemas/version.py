"""Version-history schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserSummary


class VersionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version_number: int
    title: str
    label: str
    author: UserSummary
    created_at: datetime


class VersionDetail(VersionSummary):
    content_html: str
