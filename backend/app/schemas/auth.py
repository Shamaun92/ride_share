"""Login payload."""
from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    identifier: str = Field(..., description="email or phone")
    password: str
