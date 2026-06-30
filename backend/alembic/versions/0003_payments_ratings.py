"""wallets, ledger, payments, ratings + ride.payment_method (Phase 4)

Revision ID: 0003_payments_ratings
Revises: 0002_rides
Create Date: 2025-01-03 00:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_payments_ratings"
down_revision: Union[str, None] = "0002_rides"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "rides",
        sa.Column(
            "payment_method",
            sa.String(length=20),
            nullable=False,
            server_default="cash",
        ),
    )

    op.create_table(
        "wallets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("balance_poisha", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="BDT"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_wallets_user_id"),
    )
    op.create_index("ix_wallets_user_id", "wallets", ["user_id"])

    op.create_table(
        "ledger_transactions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("ride_id", sa.Uuid(), nullable=True),
        sa.Column("reverses_id", sa.Uuid(), nullable=True),
        sa.Column("memo", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ride_id"], ["rides.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reverses_id"], ["ledger_transactions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ledger_transactions_kind", "ledger_transactions", ["kind"])
    op.create_index("ix_ledger_transactions_ride_id", "ledger_transactions", ["ride_id"])

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("account", sa.String(length=20), nullable=False),
        sa.Column("amount_poisha", sa.BigInteger(), nullable=False),
        sa.Column("wallet_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["transaction_id"], ["ledger_transactions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ledger_entries_transaction_id", "ledger_entries", ["transaction_id"])
    op.create_index("ix_ledger_entries_wallet_id", "ledger_entries", ["wallet_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("ride_id", sa.Uuid(), nullable=False),
        sa.Column("payer_user_id", sa.Uuid(), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("amount_poisha", sa.BigInteger(), nullable=False),
        sa.Column("commission_poisha", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("driver_earnings_poisha", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("breakdown", sa.JSON(), nullable=True),
        sa.Column("transaction_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ride_id"], ["rides.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transaction_id"], ["ledger_transactions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_payments_ride_id", "payments", ["ride_id"])
    op.create_index("ix_payments_payer_user_id", "payments", ["payer_user_id"])
    op.create_index("ix_payments_status", "payments", ["status"])

    op.create_table(
        "ratings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("ride_id", sa.Uuid(), nullable=False),
        sa.Column("rater_user_id", sa.Uuid(), nullable=False),
        sa.Column("ratee_user_id", sa.Uuid(), nullable=False),
        sa.Column("rater_role", sa.String(length=20), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("comment", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ride_id"], ["rides.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rater_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ratee_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("ride_id", "rater_user_id", name="uq_rating_ride_rater"),
        sa.CheckConstraint("score >= 1 AND score <= 5", name="ck_rating_score_range"),
    )
    op.create_index("ix_ratings_ride_id", "ratings", ["ride_id"])
    op.create_index("ix_ratings_rater_user_id", "ratings", ["rater_user_id"])
    op.create_index("ix_ratings_ratee_user_id", "ratings", ["ratee_user_id"])


def downgrade() -> None:
    op.drop_table("ratings")
    op.drop_table("payments")
    op.drop_table("ledger_entries")
    op.drop_table("ledger_transactions")
    op.drop_table("wallets")
    op.drop_column("rides", "payment_method")
