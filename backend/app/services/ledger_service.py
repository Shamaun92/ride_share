"""Double-entry ledger service.

Every financial event is a LedgerTransaction whose postings' signed amounts sum
to exactly zero. `post` enforces that invariant, writes the entries, and moves
the balance of any wallet-backed account. Callers control the transaction
boundary (post only flushes); standalone callers commit themselves.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.enums import LedgerAccount, LedgerTxnKind
from app.models.ledger import LedgerEntry, LedgerTransaction
from app.repositories.wallet import WalletRepository


@dataclass(frozen=True)
class Posting:
    account: LedgerAccount
    amount_poisha: int  # signed: + credits the account, - debits it
    wallet_id: uuid.UUID | None = None


class LedgerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.wallets = WalletRepository(session)

    async def post(
        self,
        kind: LedgerTxnKind,
        postings: list[Posting],
        *,
        ride_id: uuid.UUID | None = None,
        memo: str | None = None,
        reverses_id: uuid.UUID | None = None,
    ) -> LedgerTransaction:
        if sum(p.amount_poisha for p in postings) != 0:
            raise ValidationError("Ledger transaction does not balance")
        if not postings:
            raise ValidationError("Ledger transaction needs at least one posting")

        txn = LedgerTransaction(
            kind=kind, ride_id=ride_id, memo=memo, reverses_id=reverses_id
        )
        self.session.add(txn)
        await self.session.flush()  # assign txn.id

        for p in postings:
            self.session.add(
                LedgerEntry(
                    transaction_id=txn.id,
                    account=p.account,
                    amount_poisha=p.amount_poisha,
                    wallet_id=p.wallet_id,
                )
            )
            if p.wallet_id is not None:
                wallet = await self.wallets.get(p.wallet_id)
                if wallet is not None:
                    wallet.balance_poisha += p.amount_poisha

        await self.session.flush()
        return txn

    async def reverse(
        self, txn: LedgerTransaction, *, memo: str | None = None
    ) -> LedgerTransaction:
        """Post the mirror image of a prior transaction (a true reversal)."""
        mirror = [
            Posting(
                account=e.account,
                amount_poisha=-e.amount_poisha,
                wallet_id=e.wallet_id,
            )
            for e in txn.entries
        ]
        return await self.post(
            LedgerTxnKind.REFUND,
            mirror,
            ride_id=txn.ride_id,
            memo=memo or f"Reversal of {txn.id}",
            reverses_id=txn.id,
        )
