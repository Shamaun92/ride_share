"""DriverProfile: driver-specific attributes, 1:1 with a User(role=DRIVER).

Holds verification, availability status, live location (denormalized for fast
nearby-driver queries later), and aggregate rating. Vehicles hang off the
driver.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import DriverStatus, VerificationStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.vehicle import Vehicle


class DriverProfile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "driver_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    license_number: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status", native_enum=False),
        default=VerificationStatus.PENDING,
        nullable=False,
        index=True,
    )
    status: Mapped[DriverStatus] = mapped_column(
        Enum(DriverStatus, name="driver_status", native_enum=False),
        default=DriverStatus.OFFLINE,
        nullable=False,
        index=True,
    )
    current_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating_avg: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship(back_populates="driver_profile")
    vehicles: Mapped[list["Vehicle"]] = relationship(
        back_populates="driver",
        cascade="all, delete-orphan",
    )
