"""Cryptographic primitives: password hashing and JWT issue/verify.

Passwords: bcrypt directly (avoids the passlib/bcrypt 4.x compatibility issues).
Tokens: PyJWT. Access tokens are short-lived; refresh tokens carry a unique
`jti` so they can be individually revoked via Redis.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

ALGORITHM = settings.JWT_ALGORITHM


# --------------------------------------------------------------------------- #
# Passwords
# --------------------------------------------------------------------------- #
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except ValueError:
        return False


# --------------------------------------------------------------------------- #
# JWT
# --------------------------------------------------------------------------- #
def _create_token(
    subject: str | int,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra_claims:
        payload.update(extra_claims)
    encoded = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded, jti


def create_access_token(
    subject: str | int, role: str, extra_claims: dict[str, Any] | None = None
) -> str:
    claims = {"role": role}
    if extra_claims:
        claims.update(extra_claims)
    token, _ = _create_token(
        subject,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        claims,
    )
    return token


def create_refresh_token(subject: str | int, role: str) -> tuple[str, str]:
    """Returns (token, jti). The jti is tracked in Redis for revocation."""
    return _create_token(
        subject,
        "refresh",
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        {"role": role},
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode & verify signature/expiry. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
