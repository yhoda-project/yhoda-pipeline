"""Add industry_business, industry_business_kpi, and jobs_lsoa tables.

Revision ID: c4e5f6a7b8d9
Revises: 3a7f9d2e1c8b
Create Date: 2026-04-22 09:00:00.000000+00:00

Changes
-------
* ``jobs_lsoa`` — LSOA-level employee counts by SIC code for the Jobs
  dashboard.  Upsert key: ``(lsoa_code, year, sic_code)``.
* ``industry_business`` — MSOA-level business counts by industry and turnover
  band for the Industry dashboard.  Upsert key:
  ``(year, msoa_code, industry, turnover_band)``.
* ``industry_business_kpi`` — pre-aggregated KPI table with 3-year and 8-year
  percentage change metrics, supporting Yorkshire-wide, LAD, and MSOA
  grouping levels.  Upsert key:
  ``(grouping_level, year, lad_code, msoa_code, industry, turnover_band)``.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e5f6a7b8d9"
down_revision: str | None = "3a7f9d2e1c8b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Table: jobs_lsoa
    # ------------------------------------------------------------------
    op.create_table(
        "jobs_lsoa",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lsoa_code", sa.String(length=9), nullable=False),
        sa.Column("lsoa_name", sa.String(length=100), nullable=False),
        sa.Column("msoa_code", sa.String(length=9), nullable=False),
        sa.Column("msoa_name", sa.String(length=100), nullable=False),
        sa.Column("msoa_hcl_name", sa.String(length=100), nullable=True),
        sa.Column("lad_code", sa.String(length=9), nullable=False),
        sa.Column("lad_name", sa.String(length=100), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("sic_code", sa.Integer(), nullable=False),
        sa.Column("sic_description", sa.String(length=500), nullable=False),
        sa.Column("section", sa.String(length=200), nullable=False),
        sa.Column("division", sa.String(length=200), nullable=False),
        sa.Column("group_name", sa.String(length=200), nullable=False),
        sa.Column("employees", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs_lsoa")),
    )
    op.create_index(
        "ix_jobs_lsoa_upsert_key",
        "jobs_lsoa",
        ["lsoa_code", "year", "sic_code"],
        unique=True,
    )
    op.create_index("ix_jobs_lsoa_msoa_code", "jobs_lsoa", ["msoa_code"], unique=False)
    op.create_index("ix_jobs_lsoa_lad_code", "jobs_lsoa", ["lad_code"], unique=False)
    op.create_index("ix_jobs_lsoa_year", "jobs_lsoa", ["year"], unique=False)

    # ------------------------------------------------------------------
    # Table: industry_business
    # ------------------------------------------------------------------
    op.create_table(
        "industry_business",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("msoa_code", sa.String(length=9), nullable=False),
        sa.Column("msoa_name", sa.String(length=100), nullable=False),
        sa.Column("lad_code", sa.String(length=9), nullable=False),
        sa.Column("lad_name", sa.String(length=100), nullable=False),
        sa.Column("industry", sa.String(length=200), nullable=False),
        sa.Column("turnover_band", sa.String(length=50), nullable=False),
        sa.Column("business_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_industry_business")),
    )
    op.create_index(
        "ix_industry_business_upsert_key",
        "industry_business",
        ["year", "msoa_code", "industry", "turnover_band"],
        unique=True,
    )
    op.create_index(
        "ix_industry_business_lad_code", "industry_business", ["lad_code"], unique=False
    )
    op.create_index("ix_industry_business_year", "industry_business", ["year"], unique=False)

    # ------------------------------------------------------------------
    # Table: industry_business_kpi
    # ------------------------------------------------------------------
    op.create_table(
        "industry_business_kpi",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("grouping_level", sa.String(length=20), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("lad_code", sa.String(length=9), nullable=False, server_default="''"),
        sa.Column("lad_name", sa.String(length=100), nullable=False, server_default="''"),
        sa.Column("msoa_code", sa.String(length=9), nullable=False, server_default="''"),
        sa.Column("msoa_name", sa.String(length=100), nullable=False, server_default="''"),
        sa.Column("industry", sa.String(length=200), nullable=False, server_default="''"),
        sa.Column("turnover_band", sa.String(length=50), nullable=False),
        sa.Column("business_count", sa.Integer(), nullable=True),
        sa.Column("business_lag3", sa.Integer(), nullable=True),
        sa.Column("pct_change_3y", sa.Float(), nullable=True),
        sa.Column("business_lag8", sa.Integer(), nullable=True),
        sa.Column("pct_change_8y", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_industry_business_kpi")),
    )
    op.create_index(
        "ix_industry_kpi_upsert_key",
        "industry_business_kpi",
        ["grouping_level", "year", "lad_code", "msoa_code", "industry", "turnover_band"],
        unique=True,
    )
    op.create_index("ix_industry_kpi_lad_code", "industry_business_kpi", ["lad_code"], unique=False)
    op.create_index("ix_industry_kpi_year", "industry_business_kpi", ["year"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_industry_kpi_year", table_name="industry_business_kpi")
    op.drop_index("ix_industry_kpi_lad_code", table_name="industry_business_kpi")
    op.drop_index("ix_industry_kpi_upsert_key", table_name="industry_business_kpi")
    op.drop_table("industry_business_kpi")

    op.drop_index("ix_industry_business_year", table_name="industry_business")
    op.drop_index("ix_industry_business_lad_code", table_name="industry_business")
    op.drop_index("ix_industry_business_upsert_key", table_name="industry_business")
    op.drop_table("industry_business")

    op.drop_index("ix_jobs_lsoa_year", table_name="jobs_lsoa")
    op.drop_index("ix_jobs_lsoa_lad_code", table_name="jobs_lsoa")
    op.drop_index("ix_jobs_lsoa_msoa_code", table_name="jobs_lsoa")
    op.drop_index("ix_jobs_lsoa_upsert_key", table_name="jobs_lsoa")
    op.drop_table("jobs_lsoa")
