"""Unit tests for the crypto core (no DB/Redis needed)."""
from __future__ import annotations

import jwt
import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("s3cret-password")
    assert hashed != "s3cret-password"
    assert verify_password("s3cret-password", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_claims() -> None:
    token = create_access_token("user-1", "rider")
    payload = decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["role"] == "rider"
    assert payload["type"] == "access"


def test_refresh_token_has_unique_jti() -> None:
    _, jti1 = create_refresh_token("user-1", "driver")
    _, jti2 = create_refresh_token("user-1", "driver")
    assert jti1 != jti2


def test_tampered_token_rejected() -> None:
    token = create_access_token("user-1", "rider")
    with pytest.raises(jwt.PyJWTError):
        decode_token(token + "tampered")
