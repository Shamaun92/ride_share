"""Real-time event envelope, channel naming, and the publish helper.

Events flow: a producer (REST handler, WS handler, or RideService) publishes a
JSON envelope to the ride's Redis channel. Every API instance runs a subscriber
(see WebSocketHub) that fans the envelope out to locally-connected sockets. This
Pub/Sub backplane is what makes real-time delivery correct across horizontally
scaled instances — the publisher never needs to know which instance holds the
recipient's socket.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from redis.asyncio import Redis

CHANNEL_PREFIX = "rt:ride:"
CHANNEL_PATTERN = "rt:ride:*"
USER_CHANNEL_PREFIX = "rt:user:"
USER_CHANNEL_PATTERN = "rt:user:*"

# Patterns the hub subscribes to.
ALL_PATTERNS = [CHANNEL_PATTERN, USER_CHANNEL_PATTERN]


class EventType(str, Enum):
    SNAPSHOT = "snapshot"          # sent once on connect (current state)
    LOCATION = "location"          # driver position update
    RIDE_STATUS = "ride_status"    # lifecycle transition
    NOTIFICATION = "notification"  # user-directed notification
    PONG = "pong"                  # heartbeat reply
    ERROR = "error"


def ride_channel(ride_id: uuid.UUID | str) -> str:
    return f"{CHANNEL_PREFIX}{ride_id}"


def user_channel(user_id: uuid.UUID | str) -> str:
    return f"{USER_CHANNEL_PREFIX}{user_id}"


def ride_id_from_channel(channel: str) -> str:
    return channel[len(CHANNEL_PREFIX):]


def build_event(event_type: EventType, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": event_type.value,
        "data": data,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def encode(event: dict[str, Any]) -> str:
    return json.dumps(event, default=str)


async def publish_event(
    redis: Redis,
    ride_id: uuid.UUID | str,
    event_type: EventType,
    data: dict[str, Any],
) -> None:
    """Publish an event to a ride's channel. Best-effort: real-time delivery
    must never block or fail the originating transaction, so callers treat this
    as fire-and-forget.
    """
    await redis.publish(ride_channel(ride_id), encode(build_event(event_type, data)))


async def publish_user_event(
    redis: Redis,
    user_id: uuid.UUID | str,
    event_type: EventType,
    data: dict,
) -> None:
    """Publish an event to a user's personal channel (notifications)."""
    await redis.publish(user_channel(user_id), encode(build_event(event_type, data)))
