"""Widen industry_business_kpi.grouping_level from VARCHAR(20) to VARCHAR(50).

Revision ID: d5e6f7a8b9c0
Revises: c4e5f6a7b8d9
Create Date: 2026-04-22 11:00:00.000000+00:00

The Grouping_Level values in the KPI CSV include strings such as
``lad_turnover_industry_msoa`` (26 chars) which exceed the original
VARCHAR(20) constraint.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: str | None = "c4e5f6a7b8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "industry_business_kpi",
        "grouping_level",
        existing_type=sa.String(length=20),
        type_=sa.String(length=50),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "industry_business_kpi",
        "grouping_level",
        existing_type=sa.String(length=50),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
