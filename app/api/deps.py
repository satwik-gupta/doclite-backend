"""Dependency-injection wiring (composition root for request-scoped objects).

FastAPI ``Depends`` builds the object graph per request: a DB session yields the
repositories, which are injected into services, which receive the central policy.
Nothing instantiates concrete DB access with hardcoded globals (Dependency
Inversion). Singletons that are safe to share (settings, security, policy) are cached.

This module GROWS phase by phase: later phases append their service providers.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.exceptions import AuthenticationError
from app.core.security import SecurityManager
from app.domain.policy import PermissionPolicy
from app.models.user import User
from app.realtime.connection_manager import ConnectionManager
from app.repositories.comment_repo import CommentRepository, SuggestionRepository
from app.repositories.document_repo import DocumentRepository
from app.repositories.share_repo import ShareRepository
from app.repositories.user_repo import UserRepository
from app.repositories.version_repo import VersionRepository
from app.services.access import AccessGuard
from app.services.auth_service import AuthService
from app.services.comment_service import CommentService
from app.services.document_service import DocumentService
from app.services.export_service import ExportService
from app.services.import_service import ImportService
from app.services.sharing_service import SharingService
from app.services.suggestion_service import SuggestionService
from app.services.version_service import VersionService

# --- shared singletons -------------------------------------------------------

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[Session, Depends(get_db)]


@lru_cache
def get_security_manager() -> SecurityManager:
    return SecurityManager(get_settings())


@lru_cache
def get_policy() -> PermissionPolicy:
    return PermissionPolicy()


@lru_cache
def get_connection_manager() -> ConnectionManager:
    """Process-wide singleton so HTTP saves and WS sockets share the same rooms."""
    return ConnectionManager()


SecurityDep = Annotated[SecurityManager, Depends(get_security_manager)]
PolicyDep = Annotated[PermissionPolicy, Depends(get_policy)]
ConnectionManagerDep = Annotated[ConnectionManager, Depends(get_connection_manager)]

# --- repositories (request-scoped) ------------------------------------------


def get_user_repo(session: SessionDep) -> UserRepository:
    return UserRepository(session)


def get_document_repo(session: SessionDep) -> DocumentRepository:
    return DocumentRepository(session)


def get_share_repo(session: SessionDep) -> ShareRepository:
    return ShareRepository(session)


def get_version_repo(session: SessionDep) -> VersionRepository:
    return VersionRepository(session)


def get_comment_repo(session: SessionDep) -> CommentRepository:
    return CommentRepository(session)


def get_suggestion_repo(session: SessionDep) -> SuggestionRepository:
    return SuggestionRepository(session)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]
DocumentRepoDep = Annotated[DocumentRepository, Depends(get_document_repo)]
ShareRepoDep = Annotated[ShareRepository, Depends(get_share_repo)]
VersionRepoDep = Annotated[VersionRepository, Depends(get_version_repo)]
CommentRepoDep = Annotated[CommentRepository, Depends(get_comment_repo)]
SuggestionRepoDep = Annotated[SuggestionRepository, Depends(get_suggestion_repo)]

# --- access guard ------------------------------------------------------------


def get_access_guard(
    document_repo: DocumentRepoDep,
    share_repo: ShareRepoDep,
    policy: PolicyDep,
) -> AccessGuard:
    return AccessGuard(document_repo, share_repo, policy)


AccessGuardDep = Annotated[AccessGuard, Depends(get_access_guard)]

# --- services ----------------------------------------------------------------


def get_auth_service(user_repo: UserRepoDep, security: SecurityDep) -> AuthService:
    return AuthService(user_repo, security)


def get_document_service(
    document_repo: DocumentRepoDep,
    version_repo: VersionRepoDep,
    access: AccessGuardDep,
) -> DocumentService:
    return DocumentService(document_repo, version_repo, access)


def get_sharing_service(
    share_repo: ShareRepoDep,
    user_repo: UserRepoDep,
    access: AccessGuardDep,
) -> SharingService:
    return SharingService(share_repo, user_repo, access)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
SharingServiceDep = Annotated[SharingService, Depends(get_sharing_service)]


def get_import_service(
    documents: DocumentServiceDep, settings: SettingsDep
) -> ImportService:
    return ImportService(documents, settings)


ImportServiceDep = Annotated[ImportService, Depends(get_import_service)]


def get_version_service(
    version_repo: VersionRepoDep,
    documents: DocumentServiceDep,
    access: AccessGuardDep,
) -> VersionService:
    return VersionService(version_repo, documents, access)


VersionServiceDep = Annotated[VersionService, Depends(get_version_service)]


def get_export_service(access: AccessGuardDep) -> ExportService:
    return ExportService(access)


ExportServiceDep = Annotated[ExportService, Depends(get_export_service)]


def get_comment_service(
    comment_repo: CommentRepoDep, access: AccessGuardDep
) -> CommentService:
    return CommentService(comment_repo, access)


def get_suggestion_service(
    suggestion_repo: SuggestionRepoDep,
    documents: DocumentServiceDep,
    access: AccessGuardDep,
) -> SuggestionService:
    return SuggestionService(suggestion_repo, documents, access)


CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]
SuggestionServiceDep = Annotated[SuggestionService, Depends(get_suggestion_service)]

# --- current user ------------------------------------------------------------

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    auth_service: AuthServiceDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Missing bearer token.")
    return auth_service.user_from_token(credentials.credentials)


CurrentUserDep = Annotated[User, Depends(get_current_user)]
