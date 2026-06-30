"""Payment data access."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ledger import LedgerTransaction
from app.models.payment import Payment
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Payment, session)

    async def get_for_ride(self, ride_id: uuid.UUID) -> Payment | None:
        result = await self.session.execute(
            select(Payment)
            .where(Payment.ride_id == ride_id)
            .order_by(Payment.created_at.desc())
        )
        return result.scalars().first()

    async def get_with_transaction(self, payment_id: uuid.UUID) -> Payment | None:
        result = await self.session.execute(
            select(Payment)
            .where(Payment.id == payment_id)
            .options(
                selectinload(Payment.transaction).selectinload(
                    LedgerTransaction.entries
                )
            )
        )
        return result.scalar_one_or_none()
