"""Promo codes and their redemptions.

A promo applies a discount to a ride's fare. The discount is funded by the
platform (a PROMO_EXPENSE ledger posting) so the driver is unaffected.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import PromoKind

if TYPE_CHECKING:
    pass


class PromoCode(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "promo_codes"

    code: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    kind: Mapped[PromoKind] = mapped_column(
        Enum(PromoKind, name="promo_kind", native_enum=False), nullable=False
    )
    # PERCENT -> basis points off; FLAT -> poisha off.
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    max_discount_poisha: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    min_fare_poisha: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False
    )
    usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    per_user_limit: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PromoRedemption(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "promo_redemptions"
    __table_args__ = (
        UniqueConstraint("promo_id", "ride_id", name="uq_promo_redemption_ride"),
    )

    promo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("promo_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ride_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("rides.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    discount_poisha: Mapped[int] = mapped_column(BigInteger, nullable=False)
