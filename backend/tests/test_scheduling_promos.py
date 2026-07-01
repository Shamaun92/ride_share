"""Tests: scheduled rides, promo codes, notifications."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.services.scheduler_service import SchedulerService
from tests.helpers import (
    auth,
    go_online,
    login,
    make_admin,
    me_id,
    register_driver,
    register_rider,
    ride_body,
    run_ride_to_completion,
    topup,
)

pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------- #
# Scheduled rides
# --------------------------------------------------------------------------- #
async def test_scheduled_ride_dispatched_when_due(
    client: AsyncClient, db_session, redis_conn
) -> None:
    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])
    driver = await register_driver(client)
    dtoken = await login(client, driver["email"])
    await go_online(client, dtoken, 23.7809, 90.4078)

    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    r = await client.post(
        "/api/v1/rides", json=ride_body(scheduled_for=future), headers=auth(rtoken)
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["ride"]["status"] == "scheduled"
    assert body["drivers_notified"] == 0
    ride_id = body["ride"]["id"]

    # Nothing due yet.
    assert await SchedulerService(db_session, redis_conn).dispatch_due() == 0

    # Simulate time passing: dispatch as if 3 hours from now.
    later = datetime.now(timezone.utc) + timedelta(hours=3)
    dispatched = await SchedulerService(db_session, redis_conn).dispatch_due(now=later)
    assert dispatched == 1

    detail = (await client.get(f"/api/v1/rides/{ride_id}", headers=auth(rtoken))).json()
    assert detail["status"] == "requested"

    offers = (await client.get("/api/v1/drivers/me/offers", headers=auth(dtoken))).json()
    assert any(o["ride_id"] == ride_id for o in offers)


# --------------------------------------------------------------------------- #
# Promo codes
# --------------------------------------------------------------------------- #
async def test_promo_quote_and_settlement(client: AsyncClient, db_session) -> None:
    admin = await register_rider(client)
    atoken = await login(client, admin["email"])
    await make_admin(db_session, await me_id(client, atoken))

    # 20% off, min fare 100 BDT
    r = await client.post(
        "/api/v1/admin/promos",
        json={
            "code": "save20",
            "kind": "percent",
            "value": 2000,
            "min_fare_poisha": 10000,
            "per_user_limit": 1,
        },
        headers=auth(atoken),
    )
    assert r.status_code == 200, r.text

    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])
    driver = await register_driver(client)
    dtoken = await login(client, driver["email"])
    await go_online(client, dtoken, 23.7809, 90.4078)
    await topup(client, rtoken, 1000)

    # Preview the discount
    q = await client.post(
        "/api/v1/promos/quote",
        json={"code": "SAVE20", "fare_poisha": 20000},
        headers=auth(rtoken),
    )
    assert q.status_code == 200
    assert q.json()["discount_poisha"] == 4000  # 20% of 20000

    # Use it on a wallet ride
    ride_id = await run_ride_to_completion(
        client, rtoken, dtoken, payment_method="wallet", promo_code="SAVE20"
    )
    receipt = (await client.get(
        f"/api/v1/rides/{ride_id}/receipt", headers=auth(rtoken)
    )).json()
    bd = receipt["payment"]["breakdown"]
    gross = bd["gross_fare"]
    discount = bd["promo_discount"]
    assert discount == gross * 2000 // 10000
    # rider charged gross - discount
    assert receipt["payment"]["amount_poisha"] == gross - discount

    # ledger still balances: PROMO_EXPENSE carries the discount
    from app.models.enums import LedgerAccount
    from app.models.ledger import LedgerEntry
    from sqlalchemy import func, select

    promo_exp = (await db_session.execute(
        select(func.coalesce(func.sum(LedgerEntry.amount_poisha), 0)).where(
            LedgerEntry.account == LedgerAccount.PROMO_EXPENSE
        )
    )).scalar_one()
    assert promo_exp == -discount

    # per-user limit: second use blocked
    q2 = await client.post(
        "/api/v1/promos/quote",
        json={"code": "SAVE20", "fare_poisha": 20000},
        headers=auth(rtoken),
    )
    assert q2.status_code == 422


# --------------------------------------------------------------------------- #
# Notifications
# --------------------------------------------------------------------------- #
async def test_notifications_lifecycle(client: AsyncClient) -> None:
    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])
    driver = await register_driver(client)
    dtoken = await login(client, driver["email"])
    await go_online(client, dtoken, 23.7809, 90.4078)

    ride_id = await run_ride_to_completion(client, rtoken, dtoken, payment_method="cash")

    notifs = (await client.get("/api/v1/notifications", headers=auth(rtoken))).json()
    kinds = [n["kind"] for n in notifs["items"]]
    # accepted, arrived, started, completed all delivered to the rider
    assert {"ride_accepted", "driver_arrived", "ride_started", "ride_completed"} <= set(kinds)
    assert notifs["unread"] == len(notifs["items"])

    # mark one read
    first = notifs["items"][0]["id"]
    mr = await client.post(f"/api/v1/notifications/{first}/read", headers=auth(rtoken))
    assert mr.status_code == 204
    after = (await client.get("/api/v1/notifications", headers=auth(rtoken))).json()
    assert after["unread"] == notifs["unread"] - 1

    # mark all read
    ma = await client.post("/api/v1/notifications/read-all", headers=auth(rtoken))
    assert ma.status_code == 200
    final = (await client.get("/api/v1/notifications", headers=auth(rtoken))).json()
    assert final["unread"] == 0
