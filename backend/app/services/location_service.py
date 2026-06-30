"""Live driver locations backed by Redis GEO.

Redis is the source of truth for *current* driver positions: it answers
proximity queries in O(log N) via GEOSEARCH and survives across API instances.
The DB keeps a denormalized last-known lat/lng for durability and debugging,
but the dispatch hot path reads from Redis.

Keys:
  drivers:geo               GEO set of online drivers (member = driver_id)
  driver:loc:{driver_id}    JSON {lat,lng,ts} last-known snapshot (TTL)
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from redis.asyncio import Redis

from app.models.enums import VehicleType

_GEO_KEY = "drivers:geo"
_LOC_TTL_SECONDS = 300


def _loc_key(driver_id: uuid.UUID | str) -> str:
    return f"driver:loc:{driver_id}"


class LocationService:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def upsert(
        self, driver_id: uuid.UUID, lat: float, lng: float
    ) -> None:
        """Add/refresh a driver's live position (GEO + last-known snapshot)."""
        await self.redis.geoadd(_GEO_KEY, (lng, lat, str(driver_id)))
        await self.redis.set(
            _loc_key(driver_id),
            json.dumps(
                {"lat": lat, "lng": lng, "ts": datetime.now(timezone.utc).isoformat()}
            ),
            ex=_LOC_TTL_SECONDS,
        )

    async def remove(self, driver_id: uuid.UUID) -> None:
        """Withdraw a driver from proximity search (e.g. on going offline)."""
        await self.redis.zrem(_GEO_KEY, str(driver_id))

    async def get_last_known(
        self, driver_id: uuid.UUID
    ) -> dict[str, float | str] | None:
        raw = await self.redis.get(_loc_key(driver_id))
        return json.loads(raw) if raw else None

    async def search_nearby(
        self, lat: float, lng: float, radius_km: float, count: int
    ) -> list[tuple[str, float]]:
        """Return (driver_id, distance_km) for live drivers within the radius,
        nearest first. Vehicle-type / status filtering happens against the DB
        by the caller, since those are relational concerns.
        """
        try:
            results = await self.redis.geosearch(
                _GEO_KEY,
                longitude=lng,
                latitude=lat,
                radius=radius_km,
                unit="km",
                sort="ASC",
                count=count,
                withdist=True,
            )
        except Exception:
            return []
        out: list[tuple[str, float]] = []
        for row in results:
            # redis-py returns [member, distance] when withdist=True
            member, dist = (row[0], float(row[1])) if isinstance(row, (list, tuple)) else (row, 0.0)
            out.append((member, dist))
        return out
