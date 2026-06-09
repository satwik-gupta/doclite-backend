"""Version-history routes (list / preview / restore)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter

from app.api.deps import (
    ConnectionManagerDep,
    CurrentUserDep,
    SharingServiceDep,
    VersionServiceDep,
)
from app.api.presenters import to_detail
from app.schemas.document import DocumentDetail
from app.schemas.version import VersionDetail, VersionSummary

router = APIRouter(prefix="/api/documents", tags=["versions"])


@router.get("/{document_id}/versions", response_model=List[VersionSummary])
def list_versions(
    document_id: int, current_user: CurrentUserDep, versions: VersionServiceDep
) -> List[VersionSummary]:
    return [
        VersionSummary.model_validate(v)
        for v in versions.list_versions(current_user, document_id)
    ]


@router.get("/{document_id}/versions/{version_id}", response_model=VersionDetail)
def get_version(
    document_id: int,
    version_id: int,
    current_user: CurrentUserDep,
    versions: VersionServiceDep,
) -> VersionDetail:
    return VersionDetail.model_validate(
        versions.get_version(current_user, document_id, version_id)
    )


@router.post(
    "/{document_id}/versions/{version_id}/restore", response_model=DocumentDetail
)
async def restore_version(
    document_id: int,
    version_id: int,
    current_user: CurrentUserDep,
    versions: VersionServiceDep,
    sharing: SharingServiceDep,
    connections: ConnectionManagerDep,
) -> DocumentDetail:
    item = versions.restore_version(current_user, document_id, version_id)
    collaborators = sharing.list_collaborators(current_user, document_id)
    await connections.notify_document_updated(document_id, current_user, label="restore")
    return to_detail(item, collaborators)
