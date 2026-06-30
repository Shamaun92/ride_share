"""Ride pooling: match shared rides into pools by pickup proximity.

A shared ride either joins an OPEN pool whose pickup bucket matches or seeds a
new one. Pooled riders receive a configured discount at settlement. Pickup
buckets are a coarse grid (~POOL_MATCH_RADIUS_KM) used as a cheap match key.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import RidePoolStatus
from app.models.pool import RidePool
from app.models.ride import Ride
from app.repositories.pool import PoolRepository


class PoolService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.pools = PoolRepository(session)

    @staticmethod
    def bucket_for(lat: float, lng: float) -> str:
        # Grid size in degrees approximating the match radius (~111 km/deg).
        step = max(settings.POOL_MATCH_RADIUS_KM / 111.0, 1e-4)
        return f"{round(lat / step)}:{round(lng / step)}"

    async def match_or_create(self, ride: Ride) -> RidePool:
        bucket = self.bucket_for(ride.pickup_lat, ride.pickup_lng)
        pool = await self.pools.find_open_for_bucket(bucket)
        if pool is None:
            pool = RidePool(
                status=RidePoolStatus.OPEN,
                capacity=settings.POOL_DEFAULT_CAPACITY,
                member_count=0,
                pickup_bucket=bucket,
            )
            self.session.add(pool)
            await self.session.flush()

        ride.pool_id = pool.id
        pool.member_count += 1
        if pool.member_count >= pool.capacity:
            pool.status = RidePoolStatus.MATCHED
        await self.session.flush()
        return pool
