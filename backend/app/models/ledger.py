"""Double-entry ledger.

A LedgerTransaction groups two or more LedgerEntry postings whose signed amounts
sum to exactly zero (enforced in the service and asserted in tests). User-owned
postings carry a wallet_id and move that wallet's balance; system postings
(platform revenue, cash clearing) do not.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import LedgerAccount, LedgerTxnKind

if TYPE_CHECKING:
    from app.models.wallet import Wallet


class LedgerTransaction(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ledger_transactions"

    kind: Mapped[LedgerTxnKind] = mapped_column(
        Enum(LedgerTxnKind, name="ledger_txn_kind", native_enum=False),
        nullable=False,
        index=True,
    )
    ride_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("rides.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reverses_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ledger_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    memo: Mapped[str | None] = mapped_column(String(255), nullable=True)

    entries: Mapped[list["LedgerEntry"]] = relationship(
        back_populates="transaction",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class LedgerEntry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ledger_entries"

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ledger_transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account: Mapped[LedgerAccount] = mapped_column(
        Enum(LedgerAccount, name="ledger_account", native_enum=False),
        nullable=False,
    )
    # Signed: positive = credit to the account, negative = debit.
    amount_poisha: Mapped[int] = mapped_column(BigInteger, nullable=False)
    wallet_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("wallets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    transaction: Mapped["LedgerTransaction"] = relationship(
        back_populates="entries"
    )
    wallet: Mapped["Wallet | None"] = relationship("Wallet", lazy="selectin")
