"""Surge pricing from live supply/demand.

Surge multiplier (basis points) rises when nearby open ride requests outnumber
nearby available drivers. Supply comes from the Redis GEO index; demand from
open REQUESTED rides in the same area. Bounded by SURGE_MAX_BPS.
"""
from __future__ import annotations

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.ride import RideRepository
from app.services.location_service import LocationService


class SurgeService:
    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.session = session
        self.locations = LocationService(redis)
        self.rides = RideRepository(session)

    async def compute_bps(self, lat: float, lng: float) -> int:
        if not settings.SURGE_ENABLED:
            return 10000
        radius = settings.SURGE_DEMAND_RADIUS_KM
        nearby_drivers = await self.locations.search_nearby(lat, lng, radius, count=50)
        supply = len(nearby_drivers)
        demand = await self.rides.count_open_requests_near(lat, lng, radius)

        if supply == 0 and demand == 0:
            return 10000
        # Ratio of unmet demand to supply drives the multiplier.
        effective_supply = max(supply, 1)
        pressure = max(0.0, (demand - supply) / effective_supply)
        surge_bps = int(round(10000 * (1.0 + pressure)))
        return max(10000, min(surge_bps, settings.SURGE_MAX_BPS))
