"""RideOffer: a dispatch offer of a ride to a specific nearby driver.

Modelling dispatch as explicit offers (rather than an open pool) gives a clean
audit trail, per-driver expiry, and a natural seam for pushing offers over
WebSocket. The first driver to accept atomically claims the ride.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import OfferStatus

if TYPE_CHECKING:
    from app.models.driver import DriverProfile
    from app.models.ride import Ride


class RideOffer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ride_offers"
    __table_args__ = (
        UniqueConstraint("ride_id", "driver_id", name="uq_ride_offer_driver"),
    )

    ride_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("rides.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("driver_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[OfferStatus] = mapped_column(
        Enum(OfferStatus, name="offer_status", native_enum=False),
        default=OfferStatus.PENDING,
        nullable=False,
        index=True,
    )
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    ride: Mapped["Ride"] = relationship(back_populates="offers", lazy="selectin")
    driver: Mapped["DriverProfile"] = relationship(lazy="selectin")
