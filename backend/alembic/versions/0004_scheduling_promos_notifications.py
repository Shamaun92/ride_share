"""scheduling, promos, notifications (Phase 5)

Revision ID: 0004_sched_promo_notif
Revises: 0003_payments_ratings
Create Date: 2025-01-04 00:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_sched_promo_notif"
down_revision: Union[str, None] = "0003_payments_ratings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "promo_codes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("max_discount_poisha", sa.BigInteger(), nullable=True),
        sa.Column("min_fare_poisha", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("usage_limit", sa.Integer(), nullable=True),
        sa.Column("per_user_limit", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code", name="uq_promo_codes_code"),
    )
    op.create_index("ix_promo_codes_code", "promo_codes", ["code"])

    op.create_table(
        "promo_redemptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("promo_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("ride_id", sa.Uuid(), nullable=False),
        sa.Column("discount_poisha", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["promo_id"], ["promo_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ride_id"], ["rides.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("promo_id", "ride_id", name="uq_promo_redemption_ride"),
    )
    op.create_index("ix_promo_redemptions_promo_id", "promo_redemptions", ["promo_id"])
    op.create_index("ix_promo_redemptions_user_id", "promo_redemptions", ["user_id"])
    op.create_index("ix_promo_redemptions_ride_id", "promo_redemptions", ["ride_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("body", sa.String(length=500), nullable=False),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("ride_id", sa.Uuid(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ride_id"], ["rides.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_ride_id", "notifications", ["ride_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])

    op.add_column("rides", sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rides", sa.Column("promo_code_id", sa.Uuid(), nullable=True))
    op.add_column("rides", sa.Column("discount_poisha", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_rides_scheduled_for", "rides", ["scheduled_for"])
    op.create_foreign_key(
        "fk_rides_promo_code_id", "rides", "promo_codes",
        ["promo_code_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_rides_promo_code_id", "rides", type_="foreignkey")
    op.drop_index("ix_rides_scheduled_for", "rides")
    op.drop_column("rides", "discount_poisha")
    op.drop_column("rides", "promo_code_id")
    op.drop_column("rides", "scheduled_for")
    op.drop_table("notifications")
    op.drop_table("promo_redemptions")
    op.drop_table("promo_codes")
