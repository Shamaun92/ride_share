"""Vehicle owned by a driver. A driver may register multiple; one is active."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import VehicleType

if TYPE_CHECKING:
    from app.models.driver import DriverProfile


class Vehicle(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "vehicles"

    driver_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("driver_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vehicle_type: Mapped[VehicleType] = mapped_column(
        Enum(VehicleType, name="vehicle_type", native_enum=False),
        nullable=False,
    )
    make: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    color: Mapped[str] = mapped_column(String(32), nullable=False)
    license_plate: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    driver: Mapped["DriverProfile"] = relationship(back_populates="vehicles")
