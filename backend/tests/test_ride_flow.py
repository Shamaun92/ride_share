"""Phase 2 integration tests: dispatch, lifecycle, race, RBAC, transitions."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.helpers import (
    auth,
    go_online,
    login,
    register_driver,
    register_rider,
    ride_body,
)

pytestmark = pytest.mark.asyncio


async def test_full_happy_path(client: AsyncClient) -> None:
    rider = await register_rider(client)
    rider_token = await login(client, rider["email"])

    driver = await register_driver(client)
    driver_token = await login(client, driver["email"])
    # driver near the pickup point
    await go_online(client, driver_token, 23.7809, 90.4078)

    # rider requests
    r = await client.post("/api/v1/rides", json=ride_body(), headers=auth(rider_token))
    assert r.status_code == 201, r.text
    result = r.json()
    assert result["drivers_notified"] == 1
    ride = result["ride"]
    assert ride["status"] == "requested"
    assert ride["distance_km"] > 0
    assert ride["estimated_fare"] > 0
    ride_id = ride["id"]

    # driver sees the offer
    r = await client.get("/api/v1/drivers/me/offers", headers=auth(driver_token))
    assert r.status_code == 200
    offers = r.json()
    assert len(offers) == 1
    assert offers[0]["ride_id"] == ride_id
    assert offers[0]["distance_to_pickup_km"] >= 0

    # accept -> arrive -> start -> complete
    r = await client.post(
        f"/api/v1/drivers/me/rides/{ride_id}/accept", headers=auth(driver_token)
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "accepted"
    assert r.json()["driver"]["full_name"] == driver["full_name"]
    assert r.json()["driver"]["vehicle"]["license_plate"]

    for action, expected in [
        ("arrive", "arrived"),
        ("start", "in_progress"),
        ("complete", "completed"),
    ]:
        r = await client.post(
            f"/api/v1/drivers/me/rides/{ride_id}/{action}", headers=auth(driver_token)
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == expected

    # final fare set on completion
    r = await client.get(f"/api/v1/rides/{ride_id}", headers=auth(rider_token))
    assert r.json()["final_fare"] is not None

    # driver freed (ONLINE) and can take another
    r = await client.get("/api/v1/drivers/me", headers=auth(driver_token))
    assert r.json()["status"] == "online"


async def test_no_nearby_drivers(client: AsyncClient) -> None:
    rider = await register_rider(client)
    token = await login(client, rider["email"])
    # no drivers online at all
    r = await client.post("/api/v1/rides", json=ride_body(), headers=auth(token))
    assert r.status_code == 201
    assert r.json()["drivers_notified"] == 0


async def test_driver_too_far_not_offered(client: AsyncClient) -> None:
    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])
    driver = await register_driver(client)
    dtoken = await login(client, driver["email"])
    # ~100 km away
    await go_online(client, dtoken, 24.9000, 91.8700)
    r = await client.post("/api/v1/rides", json=ride_body(), headers=auth(rtoken))
    assert r.json()["drivers_notified"] == 0


async def test_vehicle_type_filter(client: AsyncClient) -> None:
    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])
    # nearby driver, but a bike — rider asks for a car
    driver = await register_driver(client, vehicle_type="bike")
    dtoken = await login(client, driver["email"])
    await go_online(client, dtoken, 23.7809, 90.4078)
    r = await client.post(
        "/api/v1/rides", json=ride_body(vehicle_type="car"), headers=auth(rtoken)
    )
    assert r.json()["drivers_notified"] == 0


async def test_accept_race_only_one_wins(client: AsyncClient) -> None:
    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])

    d1 = await register_driver(client)
    d2 = await register_driver(client)
    t1 = await login(client, d1["email"])
    t2 = await login(client, d2["email"])
    await go_online(client, t1, 23.7809, 90.4078)
    await go_online(client, t2, 23.7808, 90.4079)

    r = await client.post("/api/v1/rides", json=ride_body(), headers=auth(rtoken))
    assert r.json()["drivers_notified"] == 2
    ride_id = r.json()["ride"]["id"]

    r1 = await client.post(
        f"/api/v1/drivers/me/rides/{ride_id}/accept", headers=auth(t1)
    )
    r2 = await client.post(
        f"/api/v1/drivers/me/rides/{ride_id}/accept", headers=auth(t2)
    )
    assert r1.status_code == 200
    assert r2.status_code == 409  # loser gets a clean conflict

    # the loser's offer is no longer pending
    r = await client.get("/api/v1/drivers/me/offers", headers=auth(t2))
    assert r.json() == []


async def test_reject_keeps_ride_open_for_others(client: AsyncClient) -> None:
    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])
    d1 = await register_driver(client)
    d2 = await register_driver(client)
    t1 = await login(client, d1["email"])
    t2 = await login(client, d2["email"])
    await go_online(client, t1, 23.7809, 90.4078)
    await go_online(client, t2, 23.7808, 90.4079)

    r = await client.post("/api/v1/rides", json=ride_body(), headers=auth(rtoken))
    ride_id = r.json()["ride"]["id"]

    r = await client.post(
        f"/api/v1/drivers/me/rides/{ride_id}/reject", headers=auth(t1)
    )
    assert r.status_code == 204
    # d1 no longer sees it, d2 still can accept
    r = await client.get("/api/v1/drivers/me/offers", headers=auth(t1))
    assert r.json() == []
    r = await client.post(
        f"/api/v1/drivers/me/rides/{ride_id}/accept", headers=auth(t2)
    )
    assert r.status_code == 200


async def test_rider_cancel_frees_driver(client: AsyncClient) -> None:
    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])
    driver = await register_driver(client)
    dtoken = await login(client, driver["email"])
    await go_online(client, dtoken, 23.7809, 90.4078)

    r = await client.post("/api/v1/rides", json=ride_body(), headers=auth(rtoken))
    ride_id = r.json()["ride"]["id"]
    await client.post(f"/api/v1/drivers/me/rides/{ride_id}/accept", headers=auth(dtoken))

    r = await client.post(
        f"/api/v1/rides/{ride_id}/cancel",
        json={"reason": "changed my mind"},
        headers=auth(rtoken),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"
    assert r.json()["cancelled_by"] == "rider"

    r = await client.get("/api/v1/drivers/me", headers=auth(dtoken))
    assert r.json()["status"] == "online"


async def test_one_active_ride_per_rider(client: AsyncClient) -> None:
    rider = await register_rider(client)
    token = await login(client, rider["email"])
    r1 = await client.post("/api/v1/rides", json=ride_body(), headers=auth(token))
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/rides", json=ride_body(), headers=auth(token))
    assert r2.status_code == 409


async def test_invalid_transition_complete_before_start(client: AsyncClient) -> None:
    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])
    driver = await register_driver(client)
    dtoken = await login(client, driver["email"])
    await go_online(client, dtoken, 23.7809, 90.4078)
    r = await client.post("/api/v1/rides", json=ride_body(), headers=auth(rtoken))
    ride_id = r.json()["ride"]["id"]
    await client.post(f"/api/v1/drivers/me/rides/{ride_id}/accept", headers=auth(dtoken))
    # complete without start -> illegal
    r = await client.post(
        f"/api/v1/drivers/me/rides/{ride_id}/complete", headers=auth(dtoken)
    )
    assert r.status_code == 409


async def test_rbac_and_view_authorization(client: AsyncClient) -> None:
    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])
    other = await register_rider(client)
    otoken = await login(client, other["email"])

    # a rider cannot list/accept driver offers
    r = await client.get("/api/v1/drivers/me/offers", headers=auth(rtoken))
    assert r.status_code == 403

    r = await client.post("/api/v1/rides", json=ride_body(), headers=auth(rtoken))
    ride_id = r.json()["ride"]["id"]

    # another rider cannot view this ride
    r = await client.get(f"/api/v1/rides/{ride_id}", headers=auth(otoken))
    assert r.status_code == 403


async def test_cannot_go_online_without_location(client: AsyncClient) -> None:
    driver = await register_driver(client)
    token = await login(client, driver["email"])
    r = await client.patch(
        "/api/v1/drivers/me/availability",
        json={"status": "online"},
        headers=auth(token),
    )
    assert r.status_code == 422
