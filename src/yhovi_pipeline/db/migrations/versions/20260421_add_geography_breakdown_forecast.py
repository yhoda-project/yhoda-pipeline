"""Add geography level, breakdown category, and forecast dimensions to indicator table.

Revision ID: 3a7f9d2e1c8b
Revises: fb50d024ea2b
Create Date: 2026-04-21 09:00:00.000000+00:00

Changes
-------
* ``geography_code`` / ``geography_name`` / ``geography_level`` — support for
  MSOA and LSOA data alongside the existing LAD level.  Existing rows are
  backfilled with their ``lad_code`` / ``lad_name`` values and
  ``geography_level = 'lad'``.
* ``breakdown_category`` — sector or category label for breakdown indicators
  (empty string for non-breakdown rows).
* ``is_forecast`` / ``forecast_model`` — flag and label for Forecasting
  dashboard values.
* The upsert index is replaced: ``(indicator_id, lad_code, reference_period)``
  → ``(indicator_id, geography_code, reference_period, breakdown_category)``.
* Two supporting indexes added: ``lad_code`` (roll-up queries) and
  ``geography_level`` (dashboard-level filters).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3a7f9d2e1c8b"
down_revision: str | None = "fb50d024ea2b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Step 1 — Add breakdown_category and forecast columns.
    # Both have server-level defaults so no explicit backfill is needed.
    # ------------------------------------------------------------------
    op.add_column(
        "indicator",
        sa.Column(
            "breakdown_category",
            sa.String(length=100),
            nullable=False,
            server_default="''",
        ),
    )
    op.add_column(
        "indicator",
        sa.Column(
            "is_forecast",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "indicator",
        sa.Column("forecast_model", sa.String(length=100), nullable=True),
    )

    # ------------------------------------------------------------------
    # Step 2 — Add geography columns as nullable initially so we can
    # run a data migration before tightening the NOT NULL constraint.
    # ------------------------------------------------------------------
    op.add_column(
        "indicator",
        sa.Column("geography_code", sa.String(length=9), nullable=True),
    )
    op.add_column(
        "indicator",
        sa.Column("geography_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "indicator",
        sa.Column("geography_level", sa.String(length=10), nullable=True),
    )

    # ------------------------------------------------------------------
    # Step 3 — Backfill: all existing rows are LAD-level, so
    # geography_code = lad_code and geography_level = 'lad'.
    # ------------------------------------------------------------------
    op.execute(
        "UPDATE indicator "
        "SET geography_code = lad_code, "
        "    geography_name = lad_name, "
        "    geography_level = 'lad'"
    )

    # ------------------------------------------------------------------
    # Step 4 — Tighten NOT NULL now that every row is populated.
    # ------------------------------------------------------------------
    op.alter_column("indicator", "geography_code", nullable=False)
    op.alter_column("indicator", "geography_name", nullable=False)
    op.alter_column("indicator", "geography_level", nullable=False)

    # ------------------------------------------------------------------
    # Step 5 — Replace the upsert index with the broader key.
    # ------------------------------------------------------------------
    op.drop_index("ix_indicator_upsert_key", table_name="indicator")
    op.create_index(
        "ix_indicator_upsert_key",
        "indicator",
        ["indicator_id", "geography_code", "reference_period", "breakdown_category"],
        unique=True,
    )

    # ------------------------------------------------------------------
    # Step 6 — Add supporting indexes for common query patterns.
    # ------------------------------------------------------------------
    op.create_index("ix_indicator_lad_code", "indicator", ["lad_code"], unique=False)
    op.create_index("ix_indicator_geography_level", "indicator", ["geography_level"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_indicator_geography_level", table_name="indicator")
    op.drop_index("ix_indicator_lad_code", table_name="indicator")
    op.drop_index("ix_indicator_upsert_key", table_name="indicator")
    op.create_index(
        "ix_indicator_upsert_key",
        "indicator",
        ["indicator_id", "lad_code", "reference_period"],
        unique=True,
    )
    op.drop_column("indicator", "geography_level")
    op.drop_column("indicator", "geography_name")
    op.drop_column("indicator", "geography_code")
    op.drop_column("indicator", "forecast_model")
    op.drop_column("indicator", "is_forecast")
    op.drop_column("indicator", "breakdown_category")
