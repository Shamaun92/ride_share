"""Phase 3 real-time tests: GEO dispatch, hub fan-out, and event broadcasts."""
from __future__ import annotations

import asyncio
import json

import pytest
from httpx import AsyncClient

from app.ws import events
from app.ws.connection_manager import WebSocketHub
from tests.helpers import (
    auth,
    go_online,
    login,
    register_driver,
    register_rider,
    ride_body,
)

pytestmark = pytest.mark.asyncio


async def _drain(pubsub, expected_type: str, tries: int = 50):
    """Poll a pubsub for the next event of a given type."""
    for _ in range(tries):
        msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
        if msg and msg.get("type") == "message":
            event = json.loads(msg["data"])
            if event["type"] == expected_type:
                return event
        await asyncio.sleep(0.01)
    return None


# --------------------------------------------------------------------------- #
# Redis GEO location store
# --------------------------------------------------------------------------- #
async def test_geo_store_search(redis_conn) -> None:
    from app.services.location_service import LocationService
    import uuid

    svc = LocationService(redis_conn)
    near = uuid.uuid4()
    far = uuid.uuid4()
    await svc.upsert(near, 23.7809, 90.4078)
    await svc.upsert(far, 23.9000, 90.5000)

    hits = await svc.search_nearby(23.7806, 90.4074, radius_km=5, count=10)
    ids = [m for m, _ in hits]
    assert str(near) in ids
    assert str(far) not in ids
    # last-known snapshot round-trips
    snap = await svc.get_last_known(near)
    assert snap and abs(snap["lat"] - 23.7809) < 1e-6


async def test_offline_removes_from_geo(client: AsyncClient, redis_conn) -> None:
    driver = await register_driver(client)
    token = await login(client, driver["email"])
    await go_online(client, token, 23.7809, 90.4078)
    assert await redis_conn.zcard("drivers:geo") == 1

    r = await client.patch(
        "/api/v1/drivers/me/availability",
        json={"status": "offline"},
        headers=auth(token),
    )
    assert r.status_code == 200
    assert await redis_conn.zcard("drivers:geo") == 0


# --------------------------------------------------------------------------- #
# WebSocketHub pub/sub fan-out (deterministic, no server needed)
# --------------------------------------------------------------------------- #
class _FakeWS:
    def __init__(self) -> None:
        self.sent: list[str] = []
        self.accepted = False

    async def accept(self) -> None:
        self.accepted = True

    async def send_text(self, text: str) -> None:
        self.sent.append(text)


async def test_hub_fans_published_event_to_local_socket(redis_conn) -> None:
    hub = WebSocketHub()
    await hub.start(redis_conn)
    try:
        ws = _FakeWS()
        await hub.connect(events.ride_channel("ride-123"), ws)  # type: ignore[arg-type]
        assert ws.accepted

        await events.publish_event(
            redis_conn, "ride-123", events.EventType.LOCATION,
            {"driver_id": "d1", "lat": 23.78, "lng": 90.40},
        )
        for _ in range(50):
            if ws.sent:
                break
            await asyncio.sleep(0.02)

        assert ws.sent, "socket never received the published event"
        event = json.loads(ws.sent[0])
        assert event["type"] == "location"
        assert event["data"]["driver_id"] == "d1"

        # a different ride's event must NOT reach this socket
        before = len(ws.sent)
        await events.publish_event(
            redis_conn, "other-ride", events.EventType.LOCATION, {"x": 1}
        )
        await asyncio.sleep(0.1)
        assert len(ws.sent) == before
    finally:
        await hub.stop()


# --------------------------------------------------------------------------- #
# Service-level broadcasts on the ride channel
# --------------------------------------------------------------------------- #
async def _setup_accepted_ride(client: AsyncClient):
    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])
    driver = await register_driver(client)
    dtoken = await login(client, driver["email"])
    await go_online(client, dtoken, 23.7809, 90.4078)
    r = await client.post("/api/v1/rides", json=ride_body(), headers=auth(rtoken))
    ride_id = r.json()["ride"]["id"]
    return rtoken, dtoken, driver, ride_id


async def test_accept_broadcasts_ride_status(client: AsyncClient, redis_conn) -> None:
    rtoken, dtoken, driver, ride_id = await _setup_accepted_ride(client)

    ps = redis_conn.pubsub()
    await ps.subscribe(events.ride_channel(ride_id))
    await asyncio.sleep(0.05)

    r = await client.post(
        f"/api/v1/drivers/me/rides/{ride_id}/accept", headers=auth(dtoken)
    )
    assert r.status_code == 200

    event = await _drain(ps, "ride_status")
    assert event is not None
    assert event["data"]["status"] == "accepted"
    assert event["data"]["driver"]["full_name"] == driver["full_name"]
    await ps.aclose()


async def test_rest_location_update_broadcasts_to_active_ride(
    client: AsyncClient, redis_conn
) -> None:
    rtoken, dtoken, driver, ride_id = await _setup_accepted_ride(client)
    await client.post(
        f"/api/v1/drivers/me/rides/{ride_id}/accept", headers=auth(dtoken)
    )

    ps = redis_conn.pubsub()
    await ps.subscribe(events.ride_channel(ride_id))
    await asyncio.sleep(0.05)

    r = await client.patch(
        "/api/v1/drivers/me/location",
        json={"lat": 23.7790, "lng": 90.4060},
        headers=auth(dtoken),
    )
    assert r.status_code == 200

    event = await _drain(ps, "location")
    assert event is not None
    assert abs(event["data"]["lat"] - 23.7790) < 1e-6
    await ps.aclose()
