"""Ride pool data access."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RidePoolStatus
from app.models.pool import RidePool
from app.repositories.base import BaseRepository


class PoolRepository(BaseRepository[RidePool]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(RidePool, session)

    async def find_open_for_bucket(self, bucket: str) -> RidePool | None:
        result = await self.session.execute(
            select(RidePool)
            .where(
                RidePool.status == RidePoolStatus.OPEN,
                RidePool.pickup_bucket == bucket,
            )
            .order_by(RidePool.created_at.asc())
        )
        return result.scalars().first()
