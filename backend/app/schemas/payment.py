"""Wallet, payment, rating, and receipt schemas. Amounts exposed in poisha
plus a convenience BDT float."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    LedgerAccount,
    PaymentMethod,
    PaymentStatus,
    RaterRole,
)


def _bdt(poisha: int) -> float:
    return round(poisha / 100, 2)


class WalletRead(BaseModel):
    id: uuid.UUID
    balance_poisha: int
    balance_bdt: float
    currency: str

    @classmethod
    def from_wallet(cls, wallet) -> "WalletRead":
        return cls(
            id=wallet.id,
            balance_poisha=wallet.balance_poisha,
            balance_bdt=_bdt(wallet.balance_poisha),
            currency=wallet.currency,
        )


class TopUpRequest(BaseModel):
    amount_bdt: float = Field(..., gt=0, le=100000)


class LedgerEntryRead(BaseModel):
    id: uuid.UUID
    account: LedgerAccount
    amount_poisha: int
    amount_bdt: float
    created_at: datetime

    @classmethod
    def from_entry(cls, entry) -> "LedgerEntryRead":
        return cls(
            id=entry.id,
            account=entry.account,
            amount_poisha=entry.amount_poisha,
            amount_bdt=_bdt(entry.amount_poisha),
            created_at=entry.created_at,
        )


class WalletStatement(BaseModel):
    wallet: WalletRead
    entries: list[LedgerEntryRead]


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ride_id: uuid.UUID
    method: PaymentMethod
    status: PaymentStatus
    amount_poisha: int
    commission_poisha: int
    driver_earnings_poisha: int
    breakdown: dict | None
    created_at: datetime


class RatingCreate(BaseModel):
    score: int = Field(..., ge=1, le=5)
    comment: str | None = Field(None, max_length=500)


class RatingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ride_id: uuid.UUID
    rater_role: RaterRole
    score: int
    comment: str | None
    created_at: datetime


class RideReceipt(BaseModel):
    ride_id: uuid.UUID
    distance_km: float
    final_fare_bdt: float | None
    payment: PaymentRead | None
    my_rating: RatingRead | None
