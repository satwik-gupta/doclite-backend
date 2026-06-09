"""Authentication routes (thin controllers)."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import AuthServiceDep, CurrentUserDep
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserPublic

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, auth_service: AuthServiceDep) -> TokenResponse:
    user = auth_service.authenticate(payload.identifier, payload.password)
    token = auth_service.issue_token(user)
    return TokenResponse(access_token=token, user=UserPublic.model_validate(user))


@router.get("/me", response_model=UserPublic)
def me(current_user: CurrentUserDep) -> UserPublic:
    return UserPublic.model_validate(current_user)
