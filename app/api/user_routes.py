"""User lookup routes (for the share dialog's user picker)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Query

from app.api.deps import CurrentUserDep, UserRepoDep
from app.schemas.user import UserSummary

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/search", response_model=List[UserSummary])
def search_users(
    current_user: CurrentUserDep,
    users: UserRepoDep,
    q: str = Query(min_length=1, max_length=80),
) -> List[UserSummary]:
    found = users.search(q)
    # Exclude self from share suggestions.
    return [
        UserSummary.model_validate(u) for u in found if u.id != current_user.id
    ]
