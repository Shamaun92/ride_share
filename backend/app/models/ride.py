"""Ride: the core trip entity and its lifecycle.

`rider_id` references the rider User; `driver_id` is null until a driver claims
the ride. Per-transition timestamps are denormalized for analytics and SLA
reporting. `estimated_fare` is set by the pricing engine at request time and
`final_fare` on completion.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import CancelledBy, PaymentMethod, RideStatus, VehicleType

if TYPE_CHECKING:
    from app.models.driver import DriverProfile
    from app.models.ride_offer import RideOffer
    from app.models.user import User


class Ride(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "rides"

    rider_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    driver_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("driver_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[RideStatus] = mapped_column(
        Enum(RideStatus, name="ride_status", native_enum=False),
        default=RideStatus.REQUESTED,
        nullable=False,
        index=True,
    )
    vehicle_type: Mapped[VehicleType] = mapped_column(
        Enum(VehicleType, name="vehicle_type", native_enum=False),
        nullable=False,
    )
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method", native_enum=False),
        default=PaymentMethod.CASH,
        nullable=False,
    )

    # Pickup / dropoff
    pickup_lat: Mapped[float] = mapped_column(Float, nullable=False)
    pickup_lng: Mapped[float] = mapped_column(Float, nullable=False)
    pickup_address: Mapped[str] = mapped_column(String(255), nullable=False)
    dropoff_lat: Mapped[float] = mapped_column(Float, nullable=False)
    dropoff_lng: Mapped[float] = mapped_column(Float, nullable=False)
    dropoff_address: Mapped[str] = mapped_column(String(255), nullable=False)

    # Trip economics
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_fare: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_fare: Mapped[float | None] = mapped_column(Float, nullable=True)

    # When set and in the future, the ride starts SCHEDULED and is dispatched
    # by the due-ride worker.
    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    promo_code_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("promo_codes.id", ondelete="SET NULL"),
        nullable=True,
    )
    discount_poisha: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    # Surge multiplier in basis points, 10000 = 1.0x
    surge_bps: Mapped[int] = mapped_column(Integer, default=10000, nullable=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pool_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ride_pools.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Cancellation metadata
    cancelled_by: Mapped[CancelledBy | None] = mapped_column(
        Enum(CancelledBy, name="cancelled_by", native_enum=False), nullable=True
    )
    cancellation_reason: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    # Lifecycle timestamps (requested_at == created_at)
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    arrived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships (eager strategies chosen for async-safety; see note below)
    rider: Mapped["User"] = relationship(
        "User", foreign_keys=[rider_id], lazy="selectin"
    )
    driver: Mapped["DriverProfile | None"] = relationship(
        "DriverProfile", foreign_keys=[driver_id], lazy="selectin"
    )
    # `offers` is loaded explicitly when needed to avoid an offer<->ride cycle.
    offers: Mapped[list["RideOffer"]] = relationship(
        back_populates="ride",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )
