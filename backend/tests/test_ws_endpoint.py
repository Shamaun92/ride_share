"""End-to-end WebSocket test through a real ASGI connection.

Uses Starlette's TestClient (which runs the app lifespan, starting the hub) with
a file-backed SQLite DB and a shared FakeRedis server so the lifespan hub and
the request handlers talk to the same Redis.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
import uuid

import fakeredis
import fakeredis.aioredis as fakeaio
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.testclient import TestClient

import app.core.redis as redis_module
from app.core.database import get_db
from app.core.redis import get_redis
from app.main import app
from app.models.base import Base

DB_PATH = os.path.join(tempfile.gettempdir(), f"ws_phase3_{uuid.uuid4().hex}.db")
DB_URL = f"sqlite+aiosqlite:///{DB_PATH.replace(os.sep, '/')}"


async def _create_schema() -> None:
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


@pytest.fixture
def ws_client():
    asyncio.run(_create_schema())
    engine = create_async_engine(DB_URL, poolclass=NullPool)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    server = fakeredis.FakeServer()
    fake = fakeaio.FakeRedis(server=server, decode_responses=True)

    async def _get_db():
        async with Session() as session:
            yield session

    async def _get_redis():
        return fake

    # Make the lifespan's init_redis() hand back the same fake instance.
    redis_module._redis = fake
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_redis] = _get_redis

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    redis_module._redis = None
    try:
        os.remove(DB_PATH)
    except OSError:
        pass


def _register_rider(client, n):
    body = {
        "email": f"wsr{n}@example.com",
        "phone": f"+8801990{n:05d}",
        "full_name": f"WS Rider {n}",
        "password": "supersecret1",
    }
    assert client.post("/api/v1/auth/register", json=body).status_code == 201
    return body


def _register_driver(client, n):
    body = {
        "email": f"wsd{n}@example.com",
        "phone": f"+8801880{n:05d}",
        "full_name": f"WS Driver {n}",
        "password": "supersecret1",
        "license_number": f"WS-{n:05d}",
        "vehicle": {
            "vehicle_type": "car",
            "make": "Toyota",
            "model": "Axio",
            "color": "White",
            "license_plate": f"WS-GA-{n:04d}",
        },
    }
    assert client.post("/api/v1/auth/register/driver", json=body).status_code == 201
    return body


def _login(client, identifier):
    r = client.post(
        "/api/v1/auth/login",
        json={"identifier": identifier, "password": "supersecret1"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _recv_type(ws, wanted, max_msgs=8):
    """Read frames until one of `wanted` types arrives."""
    for _ in range(max_msgs):
        event = ws.receive_json()
        if event["type"] in wanted:
            return event
    raise AssertionError(f"did not receive any of {wanted}")


def test_ws_rejects_bad_token(ws_client) -> None:
    rider = _register_rider(ws_client, 1)
    rtoken = _login(ws_client, rider["email"])
    r = ws_client.post("/api/v1/rides", json={
        "pickup_lat": 23.7806, "pickup_lng": 90.4074, "pickup_address": "Gulshan",
        "dropoff_lat": 23.7510, "dropoff_lng": 90.3935, "dropoff_address": "Banani",
        "vehicle_type": "car",
    }, headers=_auth(rtoken))
    ride_id = r.json()["ride"]["id"]

    from starlette.testclient import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with ws_client.websocket_connect(
            f"/api/v1/ws/rides/{ride_id}?token=not-a-real-token"
        ) as ws:
            ws.receive_json()


def test_ws_full_live_tracking(ws_client) -> None:
    rider = _register_rider(ws_client, 2)
    rtoken = _login(ws_client, rider["email"])
    driver = _register_driver(ws_client, 2)
    dtoken = _login(ws_client, driver["email"])

    # driver online near pickup
    ws_client.patch("/api/v1/drivers/me/location",
                    json={"lat": 23.7809, "lng": 90.4078}, headers=_auth(dtoken))
    ws_client.patch("/api/v1/drivers/me/availability",
                    json={"status": "online"}, headers=_auth(dtoken))

    # rider requests
    r = ws_client.post("/api/v1/rides", json={
        "pickup_lat": 23.7806, "pickup_lng": 90.4074, "pickup_address": "Gulshan",
        "dropoff_lat": 23.7510, "dropoff_lng": 90.3935, "dropoff_address": "Banani",
        "vehicle_type": "car",
    }, headers=_auth(rtoken))
    assert r.json()["drivers_notified"] == 1
    ride_id = r.json()["ride"]["id"]

    # rider connects and gets a snapshot
    with ws_client.websocket_connect(
        f"/api/v1/ws/rides/{ride_id}?token={rtoken}"
    ) as rider_ws:
        snap = _recv_type(rider_ws, {"snapshot"})
        assert snap["data"]["status"] == "requested"

        # driver accepts (REST) -> rider should receive ride_status accepted
        acc = ws_client.post(
            f"/api/v1/drivers/me/rides/{ride_id}/accept", headers=_auth(dtoken)
        )
        assert acc.status_code == 200
        status_evt = _recv_type(rider_ws, {"ride_status"})
        assert status_evt["data"]["status"] == "accepted"
        assert status_evt["data"]["driver"]["full_name"] == driver["full_name"]

        # driver connects and streams a location -> rider receives it
        with ws_client.websocket_connect(
            f"/api/v1/ws/rides/{ride_id}?token={dtoken}"
        ) as driver_ws:
            _recv_type(driver_ws, {"snapshot"})
            driver_ws.send_json({"type": "location", "lat": 23.7795, "lng": 90.4065})
            loc = _recv_type(rider_ws, {"location"})
            assert abs(loc["data"]["lat"] - 23.7795) < 1e-6

            # heartbeat
            driver_ws.send_json({"type": "ping"})
            pong = _recv_type(driver_ws, {"pong"})
            assert pong["type"] == "pong"
