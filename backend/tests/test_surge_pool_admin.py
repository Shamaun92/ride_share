"""Tests: surge pricing, ride pooling, admin dashboard."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

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
# Surge
# --------------------------------------------------------------------------- #
async def test_surge_preview_no_pressure_is_baseline(client: AsyncClient) -> None:
    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])
    driver = await register_driver(client)
    dtoken = await login(client, driver["email"])
    await go_online(client, dtoken, 23.7806, 90.4074)

    # One driver, no open requests -> no surge.
    r = await client.get(
        "/api/v1/pricing/surge",
        params={"lat": 23.7806, "lng": 90.4074},
        headers=auth(rtoken),
    )
    assert r.status_code == 200
    assert r.json()["surge_bps"] == 10000
    assert r.json()["surge_multiplier"] == 1.0


async def test_surge_rises_with_unmet_demand(client: AsyncClient) -> None:
    # Several riders request near a point with no drivers online -> demand > supply.
    pt = {"lat": 23.7806, "lng": 90.4074}
    requesters = []
    for _ in range(3):
        rider = await register_rider(client)
        tok = await login(client, rider["email"])
        requesters.append(tok)
        await client.post("/api/v1/rides", json=ride_body(), headers=auth(tok))

    observer = await register_rider(client)
    otoken = await login(client, observer["email"])
    r = await client.get("/api/v1/pricing/surge", params=pt, headers=auth(otoken))
    assert r.status_code == 200
    assert r.json()["surge_bps"] > 10000


# --------------------------------------------------------------------------- #
# Pooling
# --------------------------------------------------------------------------- #
async def test_shared_rides_match_into_pool_and_discount(
    client: AsyncClient,
) -> None:
    # Two shared rides with the same pickup share a pool.
    r1user = await register_rider(client)
    r1 = await login(client, r1user["email"])
    r2user = await register_rider(client)
    r2 = await login(client, r2user["email"])
    driver = await register_driver(client)
    dtoken = await login(client, driver["email"])
    await go_online(client, dtoken, 23.7809, 90.4078)

    a = await client.post("/api/v1/rides", json=ride_body(shared=True), headers=auth(r1))
    b = await client.post("/api/v1/rides", json=ride_body(shared=True), headers=auth(r2))
    ride_a = a.json()["ride"]
    ride_b = b.json()["ride"]
    assert ride_a["is_shared"] and ride_b["is_shared"]

    # Both rides carry the same pool via the detail view.
    da = (await client.get(f"/api/v1/rides/{ride_a['id']}", headers=auth(r1))).json()
    assert da["is_shared"] is True

    # Pooled fare is discounted vs a solo ride of the same trip.
    solo_user = await register_rider(client)
    solo = await login(client, solo_user["email"])
    solo_ride = (await client.post(
        "/api/v1/rides", json=ride_body(), headers=auth(solo)
    )).json()["ride"]
    assert ride_a["estimated_fare"] < solo_ride["estimated_fare"]


async def test_pooled_ride_settles_with_discount(client: AsyncClient) -> None:
    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])
    driver = await register_driver(client)
    dtoken = await login(client, driver["email"])
    await go_online(client, dtoken, 23.7809, 90.4078)
    await topup(client, rtoken, 1000)

    ride_id = await run_ride_to_completion(
        client, rtoken, dtoken, payment_method="wallet", shared=True
    )
    receipt = (await client.get(
        f"/api/v1/rides/{ride_id}/receipt", headers=auth(rtoken)
    )).json()
    bd = receipt["payment"]["breakdown"]
    # gross fare reflects the 25% pool discount off the computed total
    assert bd["gross_fare"] == bd["total"] * 7500 // 10000


# --------------------------------------------------------------------------- #
# Admin
# --------------------------------------------------------------------------- #
async def test_admin_requires_role(client: AsyncClient) -> None:
    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])
    r = await client.get("/api/v1/admin/metrics", headers=auth(rtoken))
    assert r.status_code == 403


async def test_admin_metrics_and_management(client: AsyncClient, db_session) -> None:
    admin = await register_rider(client)
    atoken = await login(client, admin["email"])
    await make_admin(db_session, await me_id(client, atoken))

    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])
    driver = await register_driver(client)
    dtoken = await login(client, driver["email"])
    await go_online(client, dtoken, 23.7809, 90.4078)
    ride_id = await run_ride_to_completion(client, rtoken, dtoken, payment_method="cash")

    m = (await client.get("/api/v1/admin/metrics", headers=auth(atoken))).json()
    assert m["rides_by_status"].get("completed", 0) >= 1
    assert m["platform_revenue_poisha"] > 0
    assert m["total_users"] >= 3

    rides = (await client.get("/api/v1/admin/rides", headers=auth(atoken))).json()
    assert any(rd["id"] == ride_id for rd in rides)

    drivers = (await client.get("/api/v1/admin/drivers", headers=auth(atoken))).json()
    assert len(drivers) >= 1
    driver_id = drivers[0]["id"]

    v = await client.patch(
        f"/api/v1/admin/drivers/{driver_id}/verify",
        json={"status": "approved"},
        headers=auth(atoken),
    )
    assert v.status_code == 200
    assert v.json()["verification_status"] == "approved"


async def test_admin_refund_reverses_ledger(client: AsyncClient, db_session) -> None:
    admin = await register_rider(client)
    atoken = await login(client, admin["email"])
    await make_admin(db_session, await me_id(client, atoken))

    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])
    driver = await register_driver(client)
    dtoken = await login(client, driver["email"])
    await go_online(client, dtoken, 23.7809, 90.4078)
    await topup(client, rtoken, 1000)
    ride_id = await run_ride_to_completion(
        client, rtoken, dtoken, payment_method="wallet"
    )

    receipt = (await client.get(
        f"/api/v1/rides/{ride_id}/receipt", headers=auth(rtoken)
    )).json()
    payment_id = receipt["payment"]["id"]
    driver_balance_before = (await client.get(
        "/api/v1/wallet", headers=auth(dtoken)
    )).json()["wallet"]["balance_poisha"]

    rf = await client.post(
        f"/api/v1/admin/payments/{payment_id}/refund", headers=auth(atoken)
    )
    assert rf.status_code == 200
    assert rf.json()["status"] == "refunded"

    # driver earnings clawed back by the reversal
    driver_balance_after = (await client.get(
        "/api/v1/wallet", headers=auth(dtoken)
    )).json()["wallet"]["balance_poisha"]
    assert driver_balance_after == driver_balance_before - receipt["payment"]["driver_earnings_poisha"]
