"""Payment: the settlement record for a ride.

Captures the chosen method, the amounts (in poisha), the commission split, and a
snapshot of the fare breakdown. The canonical money movement is the linked
ledger transaction; `ride.final_fare` is only a display projection.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, BigInteger, Enum, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import PaymentMethod, PaymentStatus

if TYPE_CHECKING:
    from app.models.ledger import LedgerTransaction


class Payment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "payments"

    ride_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("rides.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payer_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method", native_enum=False),
        nullable=False,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", native_enum=False),
        default=PaymentStatus.PENDING,
        nullable=False,
        index=True,
    )
    amount_poisha: Mapped[int] = mapped_column(BigInteger, nullable=False)
    commission_poisha: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False
    )
    driver_earnings_poisha: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False
    )
    breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ledger_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )

    transaction: Mapped["LedgerTransaction | None"] = relationship(
        "LedgerTransaction", lazy="selectin"
    )
