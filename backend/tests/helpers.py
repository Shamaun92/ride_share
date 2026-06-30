"""Test helpers for registering/authenticating riders and drivers."""
from __future__ import annotations

from httpx import AsyncClient

_counter = {"n": 0}


def _uniq() -> int:
    _counter["n"] += 1
    return _counter["n"]


async def register_rider(client: AsyncClient, **over) -> dict:
    n = _uniq()
    body = {
        "email": over.get("email", f"rider{n}@example.com"),
        "phone": over.get("phone", f"+88017100{n:05d}"),
        "full_name": over.get("full_name", f"Rider {n}"),
        "password": "supersecret1",
    }
    r = await client.post("/api/v1/auth/register", json=body)
    assert r.status_code == 201, r.text
    return body


async def register_driver(client: AsyncClient, plate: str | None = None, **over) -> dict:
    n = _uniq()
    body = {
        "email": over.get("email", f"driver{n}@example.com"),
        "phone": over.get("phone", f"+88018100{n:05d}"),
        "full_name": over.get("full_name", f"Driver {n}"),
        "password": "supersecret1",
        "license_number": over.get("license_number", f"DHK-{n:05d}"),
        "vehicle": {
            "vehicle_type": over.get("vehicle_type", "car"),
            "make": "Toyota",
            "model": "Axio",
            "color": "White",
            "license_plate": plate or f"DHA-GA-{n:04d}",
        },
    }
    r = await client.post("/api/v1/auth/register/driver", json=body)
    assert r.status_code == 201, r.text
    return body


async def login(client: AsyncClient, identifier: str, password: str = "supersecret1") -> str:
    r = await client.post(
        "/api/v1/auth/login", json={"identifier": identifier, "password": password}
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def go_online(client: AsyncClient, token: str, lat: float, lng: float) -> None:
    r = await client.patch(
        "/api/v1/drivers/me/location", json={"lat": lat, "lng": lng}, headers=auth(token)
    )
    assert r.status_code == 200, r.text
    r = await client.patch(
        "/api/v1/drivers/me/availability", json={"status": "online"}, headers=auth(token)
    )
    assert r.status_code == 200, r.text


# A short trip in central Dhaka.
PICKUP = {"pickup_lat": 23.7806, "pickup_lng": 90.4074, "pickup_address": "Gulshan 1"}
DROPOFF = {"dropoff_lat": 23.7510, "dropoff_lng": 90.3935, "dropoff_address": "Banani"}


def ride_body(**over) -> dict:
    body = {**PICKUP, **DROPOFF, "vehicle_type": "car"}
    body.update(over)
    return body


async def me_id(client: AsyncClient, token: str) -> str:
    r = await client.get("/api/v1/users/me", headers=auth(token))
    assert r.status_code == 200, r.text
    return r.json()["id"]


async def topup(client: AsyncClient, token: str, amount_bdt: float) -> dict:
    r = await client.post(
        "/api/v1/wallet/topup", json={"amount_bdt": amount_bdt}, headers=auth(token)
    )
    assert r.status_code == 200, r.text
    return r.json()


async def run_ride_to_completion(
    client: AsyncClient, rtoken: str, dtoken: str, **ride_over
) -> str:
    """Request -> accept -> arrive -> start -> complete. Returns ride_id."""
    r = await client.post(
        "/api/v1/rides", json=ride_body(**ride_over), headers=auth(rtoken)
    )
    assert r.status_code == 201, r.text
    ride_id = r.json()["ride"]["id"]
    for path in (
        f"/api/v1/drivers/me/rides/{ride_id}/accept",
        f"/api/v1/drivers/me/rides/{ride_id}/arrive",
        f"/api/v1/drivers/me/rides/{ride_id}/start",
        f"/api/v1/drivers/me/rides/{ride_id}/complete",
    ):
        rr = await client.post(path, headers=auth(dtoken))
        assert rr.status_code == 200, rr.text
    return ride_id


async def make_admin(db_session, user_id: str) -> None:
    """Promote a user to ADMIN directly (admin bootstrap secret is unset in tests)."""
    import uuid as _uuid

    from app.models.enums import UserRole
    from app.models.user import User

    user = await db_session.get(User, _uuid.UUID(user_id))
    user.role = UserRole.ADMIN
    await db_session.commit()
