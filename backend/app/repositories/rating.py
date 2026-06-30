"""Rating data access."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rating import Rating
from app.repositories.base import BaseRepository


class RatingRepository(BaseRepository[Rating]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Rating, session)

    async def get_for_ride_and_rater(
        self, ride_id: uuid.UUID, rater_user_id: uuid.UUID
    ) -> Rating | None:
        result = await self.session.execute(
            select(Rating).where(
                Rating.ride_id == ride_id,
                Rating.rater_user_id == rater_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_ride(self, ride_id: uuid.UUID) -> list[Rating]:
        result = await self.session.execute(
            select(Rating).where(Rating.ride_id == ride_id)
        )
        return list(result.scalars().all())
