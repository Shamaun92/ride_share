"""Hardening tests: request context, security headers, rate limiting,
idempotency, and audit logging."""
from __future__ import annotations

import logging

import pytest
from httpx import AsyncClient

from app.core import redis as redis_module
from tests.helpers import auth, login, register_rider, topup

pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------- #
# Request context + security headers
# --------------------------------------------------------------------------- #
async def test_request_id_and_security_headers(client: AsyncClient) -> None:
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"


async def test_incoming_request_id_is_echoed(client: AsyncClient) -> None:
    r = await client.get("/health", headers={"X-Request-ID": "trace-abc-123"})
    assert r.headers.get("X-Request-ID") == "trace-abc-123"


# --------------------------------------------------------------------------- #
# Rate limiting
# --------------------------------------------------------------------------- #
async def test_rate_limit_returns_429(client: AsyncClient, monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "RATE_LIMIT_DEFAULT_PER_MIN", 3)

    rider = await register_rider(client)
    token = await login(client, rider["email"])

    statuses = []
    for _ in range(5):
        r = await client.post(
            "/api/v1/wallet/topup", json={"amount_bdt": 10}, headers=auth(token)
        )
        statuses.append(r.status_code)

    assert statuses[:3] == [200, 200, 200]
    assert 429 in statuses[3:]


# --------------------------------------------------------------------------- #
# Idempotency
# --------------------------------------------------------------------------- #
async def test_idempotent_topup_not_double_charged(
    client: AsyncClient, redis_conn
) -> None:
    redis_module._redis = redis_conn  # enable idempotency middleware
    try:
        rider = await register_rider(client)
        token = await login(client, rider["email"])
        headers = {**auth(token), "Idempotency-Key": "topup-key-1"}

        r1 = await client.post(
            "/api/v1/wallet/topup", json={"amount_bdt": 100}, headers=headers
        )
        assert r1.status_code == 200
        assert r1.headers.get("X-Idempotent-Replay") is None

        r2 = await client.post(
            "/api/v1/wallet/topup", json={"amount_bdt": 100}, headers=headers
        )
        assert r2.status_code == 200
        assert r2.headers.get("X-Idempotent-Replay") == "true"

        # Wallet credited only once despite two identical requests.
        wallet = (await client.get("/api/v1/wallet", headers=auth(token))).json()
        assert wallet["wallet"]["balance_poisha"] == 10000
    finally:
        redis_module._redis = None


# --------------------------------------------------------------------------- #
# Audit logging
# --------------------------------------------------------------------------- #
async def test_login_emits_audit_log(client: AsyncClient, caplog) -> None:
    rider = await register_rider(client)
    with caplog.at_level(logging.INFO, logger="audit"):
        await login(client, rider["email"])
    assert any("auth.login" in rec.message for rec in caplog.records)
