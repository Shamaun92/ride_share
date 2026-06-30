"""Promo code data access."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.promo import PromoCode, PromoRedemption
from app.repositories.base import BaseRepository


class PromoRepository(BaseRepository[PromoCode]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(PromoCode, session)

    async def get_by_code(self, code: str) -> PromoCode | None:
        result = await self.session.execute(
            select(PromoCode).where(PromoCode.code == code.upper())
        )
        return result.scalar_one_or_none()


class PromoRedemptionRepository(BaseRepository[PromoRedemption]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(PromoRedemption, session)

    async def count_for_user(self, promo_id: uuid.UUID, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(PromoRedemption)
            .where(
                PromoRedemption.promo_id == promo_id,
                PromoRedemption.user_id == user_id,
            )
        )
        return int(result.scalar_one())
