"""Wallet: a user's stored balance in poisha.

The wallet balance is a denormalized projection of the ledger — every change to
it is accompanied by balanced ledger postings (see LedgerEntry). One wallet per
user (riders and drivers both have one).
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class Wallet(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "wallets"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    balance_poisha: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="BDT", nullable=False)

    user: Mapped["User"] = relationship("User", lazy="selectin")
