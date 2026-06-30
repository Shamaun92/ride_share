"""rides + ride_offers (Phase 2)

Revision ID: 0002_rides
Revises: 0001_initial
Create Date: 2025-01-02 00:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_rides"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rides",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("rider_id", sa.Uuid(), nullable=False),
        sa.Column("driver_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="requested"),
        sa.Column("vehicle_type", sa.String(length=20), nullable=False),
        sa.Column("pickup_lat", sa.Float(), nullable=False),
        sa.Column("pickup_lng", sa.Float(), nullable=False),
        sa.Column("pickup_address", sa.String(length=255), nullable=False),
        sa.Column("dropoff_lat", sa.Float(), nullable=False),
        sa.Column("dropoff_lng", sa.Float(), nullable=False),
        sa.Column("dropoff_address", sa.String(length=255), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("estimated_fare", sa.Float(), nullable=True),
        sa.Column("final_fare", sa.Float(), nullable=True),
        sa.Column("cancelled_by", sa.String(length=20), nullable=True),
        sa.Column("cancellation_reason", sa.String(length=255), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("arrived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["rider_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["driver_id"], ["driver_profiles.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_rides_rider_id", "rides", ["rider_id"])
    op.create_index("ix_rides_driver_id", "rides", ["driver_id"])
    op.create_index("ix_rides_status", "rides", ["status"])

    op.create_table(
        "ride_offers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("ride_id", sa.Uuid(), nullable=False),
        sa.Column("driver_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ride_id"], ["rides.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["driver_id"], ["driver_profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("ride_id", "driver_id", name="uq_ride_offer_driver"),
    )
    op.create_index("ix_ride_offers_ride_id", "ride_offers", ["ride_id"])
    op.create_index("ix_ride_offers_driver_id", "ride_offers", ["driver_id"])
    op.create_index("ix_ride_offers_status", "ride_offers", ["status"])


def downgrade() -> None:
    op.drop_table("ride_offers")
    op.drop_table("rides")
