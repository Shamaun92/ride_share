"""WebSocket endpoint for live ride tracking.

One socket per ride (`/ws/rides/{ride_id}`) carries both directions:
  - rider + assigned driver receive `location` and `ride_status` events;
  - the assigned driver may *send* `location` messages (and `ping`).

Auth is via a JWT in the `token` query parameter (browsers can't set headers on
the WS handshake). Membership is authorized once at connect. On connect we push
a `snapshot` so a reconnecting client is immediately consistent.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import decode_token
from app.models.enums import UserRole
from app.models.ride import Ride
from app.models.user import User
from app.repositories.driver import DriverRepository
from app.repositories.ride import RideRepository
from app.repositories.user import UserRepository
from app.services.location_service import LocationService
from app.ws import events
from app.ws.connection_manager import hub

router = APIRouter(tags=["realtime"])

# Custom close codes (4000-4999 are application-defined).
WS_INVALID_TOKEN = 4401
WS_FORBIDDEN = 4403
WS_NOT_FOUND = 4404


async def _resolve_user(session: AsyncSession, token: str | None) -> User | None:
    if not token:
        return None
    try:
        payload = decode_token(token)
    except Exception:
        return None
    if payload.get("type") != "access":
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        user_id = uuid.UUID(sub)
    except (ValueError, TypeError):
        return None
    return await UserRepository(session).get(user_id)


async def _driver_profile_id(session: AsyncSession, user: User) -> uuid.UUID | None:
    profile = await DriverRepository(session).get_by_user_id(user.id)
    return profile.id if profile else None


async def _snapshot(
    redis: Redis, ride: Ride
) -> dict:
    driver_location = None
    if ride.driver_id is not None:
        driver_location = await LocationService(redis).get_last_known(ride.driver_id)
    return {
        "ride_id": str(ride.id),
        "status": ride.status.value,
        "driver_id": str(ride.driver_id) if ride.driver_id else None,
        "driver_location": driver_location,
    }


@router.websocket("/ws/rides/{ride_id}")
async def ride_socket(
    websocket: WebSocket,
    ride_id: uuid.UUID,
    token: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    user = await _resolve_user(session, token)
    if user is None:
        await websocket.close(code=WS_INVALID_TOKEN)
        return

    ride = await RideRepository(session).get_detail(ride_id)
    if ride is None:
        await websocket.close(code=WS_NOT_FOUND)
        return

    # Authorize membership and determine whether this connection may stream.
    is_rider = ride.rider_id == user.id
    driver_profile_id: uuid.UUID | None = None
    if user.role == UserRole.DRIVER:
        driver_profile_id = await _driver_profile_id(session, user)
    is_assigned_driver = (
        driver_profile_id is not None and ride.driver_id == driver_profile_id
    )
    if not (is_rider or is_assigned_driver):
        await websocket.close(code=WS_FORBIDDEN)
        return

    topic = events.ride_channel(ride_id)
    await hub.connect(topic, websocket)
    try:
        # Immediate consistency for (re)connects.
        await hub.send_personal(
            websocket,
            events.encode(
                events.build_event(
                    events.EventType.SNAPSHOT, await _snapshot(redis, ride)
                )
            ),
        )

        locations = LocationService(redis)
        while True:
            msg = await websocket.receive_json()
            kind = msg.get("type")

            if kind == "ping":
                await hub.send_personal(
                    websocket,
                    events.encode(events.build_event(events.EventType.PONG, {})),
                )
                continue

            if kind == "location":
                # Only the assigned driver may publish position.
                if not is_assigned_driver:
                    await hub.send_personal(
                        websocket,
                        events.encode(
                            events.build_event(
                                events.EventType.ERROR,
                                {"detail": "Only the assigned driver can stream location"},
                            )
                        ),
                    )
                    continue
                try:
                    lat = float(msg["lat"])
                    lng = float(msg["lng"])
                except (KeyError, TypeError, ValueError):
                    await hub.send_personal(
                        websocket,
                        events.encode(
                            events.build_event(
                                events.EventType.ERROR, {"detail": "lat/lng required"}
                            )
                        ),
                    )
                    continue

                await locations.upsert(driver_profile_id, lat, lng)
                await events.publish_event(
                    redis,
                    ride_id,
                    events.EventType.LOCATION,
                    {"driver_id": str(driver_profile_id), "lat": lat, "lng": lng},
                )
                continue
            # Unknown message types are ignored (forward-compatible).
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(topic, websocket)


@router.websocket("/ws/notifications")
async def notifications_socket(
    websocket: WebSocket,
    token: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Per-user notification stream. Authenticated via the `token` query param."""
    user = await _resolve_user(session, token)
    if user is None:
        await websocket.close(code=WS_INVALID_TOKEN)
        return

    channel = events.user_channel(user.id)
    await hub.connect(channel, websocket)
    try:
        while True:
            msg = await websocket.receive_json()
            if msg.get("type") == "ping":
                await hub.send_personal(
                    websocket,
                    events.encode(events.build_event(events.EventType.PONG, {})),
                )
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(channel, websocket)
