"""Auth token payloads."""
from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.models.enums import UserRole


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPayload(BaseModel):
    """Decoded JWT claims we rely on."""

    sub: uuid.UUID
    role: UserRole
    type: str
    jti: str
    exp: int
