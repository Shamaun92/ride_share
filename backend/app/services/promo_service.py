"""Promo code validation and redemption.

`quote` validates a code for a user against a fare and returns the discount in
poisha (without persisting). `redeem` records the redemption and increments
usage — called inside the settlement transaction.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.enums import PromoKind
from app.models.promo import PromoCode, PromoRedemption
from app.repositories.promo import PromoRedemptionRepository, PromoRepository


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class PromoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.promos = PromoRepository(session)
        self.redemptions = PromoRedemptionRepository(session)

    def compute_discount(self, promo: PromoCode, fare_poisha: int) -> int:
        return self._discount_for(promo, fare_poisha)

    def _discount_for(self, promo: PromoCode, fare_poisha: int) -> int:
        if promo.kind == PromoKind.PERCENT:
            discount = fare_poisha * promo.value // 10000
        else:
            discount = promo.value
        if promo.max_discount_poisha is not None:
            discount = min(discount, promo.max_discount_poisha)
        return max(0, min(discount, fare_poisha))

    async def quote(
        self, code: str, user_id: uuid.UUID, fare_poisha: int
    ) -> tuple[PromoCode, int]:
        promo = await self.promos.get_by_code(code)
        if promo is None or not promo.is_active:
            raise ValidationError("Invalid promo code")
        now = _now()
        if promo.valid_from and _aware(promo.valid_from) > now:
            raise ValidationError("Promo code is not active yet")
        if promo.valid_until and _aware(promo.valid_until) < now:
            raise ValidationError("Promo code has expired")
        if promo.usage_limit is not None and promo.used_count >= promo.usage_limit:
            raise ValidationError("Promo code usage limit reached")
        if fare_poisha < promo.min_fare_poisha:
            raise ValidationError("Fare below promo minimum")
        used = await self.redemptions.count_for_user(promo.id, user_id)
        if used >= promo.per_user_limit:
            raise ValidationError("Promo code already used")
        discount = self._discount_for(promo, fare_poisha)
        if discount <= 0:
            raise ValidationError("Promo yields no discount for this fare")
        return promo, discount

    async def redeem(
        self,
        promo: PromoCode,
        user_id: uuid.UUID,
        ride_id: uuid.UUID,
        discount_poisha: int,
    ) -> None:
        self.session.add(
            PromoRedemption(
                promo_id=promo.id,
                user_id=user_id,
                ride_id=ride_id,
                discount_poisha=discount_poisha,
            )
        )
        promo.used_count += 1
        await self.session.flush()
