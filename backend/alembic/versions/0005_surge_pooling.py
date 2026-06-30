"""surge pricing + ride pooling (Phase 6)

Revision ID: 0005_surge_pooling
Revises: 0004_sched_promo_notif
Create Date: 2025-01-05 00:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_surge_pooling"
down_revision: Union[str, None] = "0004_sched_promo_notif"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ride_pools",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("member_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pickup_bucket", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ride_pools_status", "ride_pools", ["status"])

    op.add_column("rides", sa.Column("surge_bps", sa.Integer(), nullable=False, server_default="10000"))
    op.add_column("rides", sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("rides", sa.Column("pool_id", sa.Uuid(), nullable=True))
    op.create_index("ix_rides_pool_id", "rides", ["pool_id"])
    op.create_foreign_key(
        "fk_rides_pool_id", "rides", "ride_pools", ["pool_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint("fk_rides_pool_id", "rides", type_="foreignkey")
    op.drop_index("ix_rides_pool_id", "rides")
    op.drop_column("rides", "pool_id")
    op.drop_column("rides", "is_shared")
    op.drop_column("rides", "surge_bps")
    op.drop_table("ride_pools")
