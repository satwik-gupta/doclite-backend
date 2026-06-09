"""Presenters: map service/domain objects to Pydantic response schemas.

Keeps routers thin — they call a presenter instead of hand-assembling dicts.
"""
from __future__ import annotations

from typing import List

from app.services.document_service import DocumentWithRole
from app.services.sharing_service import Collaborator
from app.schemas.document import (
    CollaboratorOut,
    DocumentDetail,
    DocumentSummary,
)
from app.schemas.user import UserSummary


def to_summary(item: DocumentWithRole) -> DocumentSummary:
    doc = item.document
    return DocumentSummary(
        id=doc.id,
        title=doc.title,
        owner=UserSummary.model_validate(doc.owner),
        my_role=item.role,
        is_owner=item.is_owner,
        updated_at=doc.updated_at,
        created_at=doc.created_at,
    )


def to_detail(item: DocumentWithRole, collaborators: List[Collaborator]) -> DocumentDetail:
    doc = item.document
    return DocumentDetail(
        id=doc.id,
        title=doc.title,
        owner=UserSummary.model_validate(doc.owner),
        my_role=item.role,
        is_owner=item.is_owner,
        updated_at=doc.updated_at,
        created_at=doc.created_at,
        content_html=doc.content_html,
        collaborators=[
            CollaboratorOut(user=UserSummary.model_validate(c.user), role=c.role)
            for c in collaborators
        ],
    )
