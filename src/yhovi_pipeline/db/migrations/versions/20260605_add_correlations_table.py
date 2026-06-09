"""Add correlations table for pre-computed Spearman correlation pairs.

Revision ID: e7f8a9b0c1d2
Revises: d5e6f7a8b9c0
Create Date: 2026-06-05 00:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e7f8a9b0c1d2"
down_revision: str | None = "d5e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "correlations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("indicator_1_id", sa.String(length=100), nullable=False),
        sa.Column("indicator_2_id", sa.String(length=100), nullable=False),
        sa.Column("indicator_1_name", sa.String(length=255), nullable=False),
        sa.Column("indicator_2_name", sa.String(length=255), nullable=False),
        sa.Column("spearman_rho", sa.Float(), nullable=True),
        sa.Column("p_value", sa.Float(), nullable=True),
        sa.Column("is_significant", sa.Boolean(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("computed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_correlations")),
    )
    op.create_index(
        "ix_correlations_upsert_key",
        "correlations",
        ["indicator_1_id", "indicator_2_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_correlations_upsert_key", table_name="correlations")
    op.drop_table("correlations")
