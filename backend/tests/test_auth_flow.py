"""Integration tests for the full auth lifecycle against SQLite + fake Redis."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

RIDER = {
    "email": "rider@example.com",
    "phone": "+8801710000001",
    "full_name": "Test Rider",
    "password": "supersecret1",
}

DRIVER = {
    "email": "driver@example.com",
    "phone": "+8801710000002",
    "full_name": "Test Driver",
    "password": "supersecret1",
    "license_number": "DHK-12345",
    "vehicle": {
        "vehicle_type": "car",
        "make": "Toyota",
        "model": "Axio",
        "color": "White",
        "license_plate": "DHA-GA-1234",
    },
}


async def test_health(client: AsyncClient) -> None:
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_rider_register_login_me(client: AsyncClient) -> None:
    r = await client.post("/api/v1/auth/register", json=RIDER)
    assert r.status_code == 201, r.text
    assert r.json()["role"] == "rider"

    # duplicate registration -> conflict
    r_dup = await client.post("/api/v1/auth/register", json=RIDER)
    assert r_dup.status_code == 409

    # login by email
    r = await client.post(
        "/api/v1/auth/login",
        json={"identifier": RIDER["email"], "password": RIDER["password"]},
    )
    assert r.status_code == 200, r.text
    tokens = r.json()
    assert tokens["access_token"] and tokens["refresh_token"]

    # access protected route
    r = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 200
    assert r.json()["email"] == RIDER["email"]


async def test_login_by_phone_and_bad_password(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=RIDER)
    r = await client.post(
        "/api/v1/auth/login",
        json={"identifier": RIDER["phone"], "password": RIDER["password"]},
    )
    assert r.status_code == 200
    r_bad = await client.post(
        "/api/v1/auth/login",
        json={"identifier": RIDER["phone"], "password": "nope"},
    )
    assert r_bad.status_code == 401


async def test_driver_register_and_rbac(client: AsyncClient) -> None:
    r = await client.post("/api/v1/auth/register/driver", json=DRIVER)
    assert r.status_code == 201, r.text
    assert r.json()["role"] == "driver"

    login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": DRIVER["email"], "password": DRIVER["password"]},
    )
    driver_token = login.json()["access_token"]

    # driver can read driver profile
    r = await client.get(
        "/api/v1/drivers/me",
        headers={"Authorization": f"Bearer {driver_token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["license_number"] == "DHK-12345"
    assert len(body["vehicles"]) == 1

    # rider is forbidden from driver-only route (RBAC)
    await client.post("/api/v1/auth/register", json=RIDER)
    rider_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": RIDER["email"], "password": RIDER["password"]},
    )
    rider_token = rider_login.json()["access_token"]
    r = await client.get(
        "/api/v1/drivers/me",
        headers={"Authorization": f"Bearer {rider_token}"},
    )
    assert r.status_code == 403


async def test_refresh_and_logout(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=RIDER)
    login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": RIDER["email"], "password": RIDER["password"]},
    )
    refresh_token = login.json()["refresh_token"]

    # refresh rotates tokens
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200, r.text
    new_refresh = r.json()["refresh_token"]

    # the old (rotated) refresh token is now revoked
    r_reuse = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert r_reuse.status_code == 401

    # logout revokes the current refresh token
    r = await client.post("/api/v1/auth/logout", json={"refresh_token": new_refresh})
    assert r.status_code == 204
    r_after = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": new_refresh}
    )
    assert r_after.status_code == 401
