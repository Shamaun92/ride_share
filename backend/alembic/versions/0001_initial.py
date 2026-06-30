"""initial schema: users, driver_profiles, vehicles

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="rider"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_phone", "users", ["phone"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "driver_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("license_number", sa.String(length=64), nullable=False),
        sa.Column("verification_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="offline"),
        sa.Column("current_lat", sa.Float(), nullable=True),
        sa.Column("current_lng", sa.Float(), nullable=True),
        sa.Column("rating_avg", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("license_number"),
    )
    op.create_index("ix_driver_profiles_user_id", "driver_profiles", ["user_id"])
    op.create_index("ix_driver_profiles_status", "driver_profiles", ["status"])
    op.create_index("ix_driver_profiles_verification_status", "driver_profiles", ["verification_status"])

    op.create_table(
        "vehicles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("driver_id", sa.Uuid(), nullable=False),
        sa.Column("vehicle_type", sa.String(length=20), nullable=False),
        sa.Column("make", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("color", sa.String(length=32), nullable=False),
        sa.Column("license_plate", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["driver_id"], ["driver_profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("license_plate"),
    )
    op.create_index("ix_vehicles_driver_id", "vehicles", ["driver_id"])
    op.create_index("ix_vehicles_license_plate", "vehicles", ["license_plate"])


def downgrade() -> None:
    op.drop_table("vehicles")
    op.drop_table("driver_profiles")
    op.drop_table("users")
