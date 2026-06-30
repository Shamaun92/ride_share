"""Wallet service: balances, top-ups, and history."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.enums import LedgerAccount, LedgerTxnKind
from app.models.wallet import Wallet
from app.repositories.wallet import LedgerRepository, WalletRepository
from app.services.ledger_service import LedgerService, Posting


class WalletService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.wallets = WalletRepository(session)
        self.ledger = LedgerService(session)
        self.ledger_repo = LedgerRepository(session)

    async def get_or_create(self, user_id: uuid.UUID) -> Wallet:
        wallet = await self.wallets.get_by_user_id(user_id)
        if wallet is None:
            wallet = Wallet(user_id=user_id, balance_poisha=0)
            self.session.add(wallet)
            await self.session.flush()
        return wallet

    async def top_up(self, user_id: uuid.UUID, amount_poisha: int) -> Wallet:
        if amount_poisha <= 0:
            raise ValidationError("Top-up amount must be positive")
        wallet = await self.get_or_create(user_id)
        # External money enters the system: cash-clearing out, wallet in.
        await self.ledger.post(
            LedgerTxnKind.TOP_UP,
            [
                Posting(LedgerAccount.CASH_CLEARING, -amount_poisha),
                Posting(
                    LedgerAccount.RIDER_WALLET, amount_poisha, wallet_id=wallet.id
                ),
            ],
            memo="Wallet top-up",
        )
        await self.session.commit()
        await self.session.refresh(wallet)
        return wallet

    async def history(self, user_id: uuid.UUID, *, limit: int = 50):
        wallet = await self.get_or_create(user_id)
        entries = await self.ledger_repo.list_entries_for_wallet(
            wallet.id, limit=limit
        )
        return wallet, entries
