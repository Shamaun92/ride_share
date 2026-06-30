"""Rating: one per (ride, rater). Riders rate drivers and vice versa.

When a driver is rated, the aggregate on DriverProfile (rating_avg/rating_count)
is updated incrementally so reads stay O(1).
"""
from __future__ import annotations

import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    Enum,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import RaterRole


class Rating(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("ride_id", "rater_user_id", name="uq_rating_ride_rater"),
        CheckConstraint("score >= 1 AND score <= 5", name="ck_rating_score_range"),
    )

    ride_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("rides.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rater_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ratee_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rater_role: Mapped[RaterRole] = mapped_column(
        Enum(RaterRole, name="rater_role", native_enum=False), nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
