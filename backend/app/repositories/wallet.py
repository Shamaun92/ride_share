"""Wallet and ledger data access."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ledger import LedgerEntry, LedgerTransaction
from app.models.wallet import Wallet
from app.repositories.base import BaseRepository


class WalletRepository(BaseRepository[Wallet]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Wallet, session)

    async def get_by_user_id(self, user_id: uuid.UUID) -> Wallet | None:
        result = await self.session.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        return result.scalar_one_or_none()


class LedgerRepository(BaseRepository[LedgerTransaction]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(LedgerTransaction, session)

    async def list_entries_for_wallet(
        self, wallet_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> list[LedgerEntry]:
        result = await self.session.execute(
            select(LedgerEntry)
            .where(LedgerEntry.wallet_id == wallet_id)
            .order_by(LedgerEntry.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
