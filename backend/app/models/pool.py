"""RidePool: a group of shared (pooled) rides served together.

Pooling lives at the matching + billing layer: shared rides with nearby pickups
are grouped into a pool and each pooled rider receives a discount. Full
multi-stop trip sequencing is the next iteration.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import RidePoolStatus

if TYPE_CHECKING:
    pass


class RidePool(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ride_pools"

    status: Mapped[RidePoolStatus] = mapped_column(
        Enum(RidePoolStatus, name="ride_pool_status", native_enum=False),
        default=RidePoolStatus.OPEN,
        nullable=False,
        index=True,
    )
    capacity: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    member_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Coarse pickup bucket used for matching (geohash-like rounded key).
    pickup_bucket: Mapped[str | None] = mapped_column(String(32), nullable=True)
