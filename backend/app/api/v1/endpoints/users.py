"""Current-user (rider/any role) endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead, summary="Get my profile")
async def read_me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)
