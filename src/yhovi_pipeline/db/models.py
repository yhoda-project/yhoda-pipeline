"""SQLAlchemy 2.0 ORM models for the YHODA data warehouse.

Design notes
------------
* Uses the new annotation-driven ``Mapped[T]`` / ``mapped_column()`` style
  (not the legacy ``Column(...)`` API).
* ``MetaData`` is initialised with a naming convention so Alembic can generate
  stable, deterministic constraint names across databases.
* All ``Enum`` columns use ``native_enum=False`` to keep the schema portable
  across database backends.
* The ``Indicator`` table has a unique index on ``(indicator_id, lad_code,
  reference_period)`` — this triple is the upsert key used by load tasks.
* ``GeoLookup`` maps LSOA codes → MSOA → LAD → Region, matching the ONS
  December 2021 geography release used throughout the project.
"""

from __future__ import annotations

import enum
from datetime import UTC, date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    Index,
    Integer,
    MetaData,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ---------------------------------------------------------------------------
# Naming convention — ensures Alembic generates deterministic constraint names
# (explicit names are required for reliable autogenerate on all backends).
# ---------------------------------------------------------------------------

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Shared declarative base — all ORM models inherit from this."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ExtractionStatus(enum.StrEnum):
    """Lifecycle state of a dataset extraction run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class Indicator(Base):
    """One row per indicator x geography x reference period x breakdown category.

    The central fact table. Each row stores a single statistical value, e.g.
    "employment rate for Bradford LAD, April 2024" or "businesses in
    manufacturing for Bradford MSOA E02002330, 2023".

    Geography levels
    ----------------
    ``lad``  — Local Authority District (the original and primary level).
    ``msoa`` — Middle Super Output Area (Industry / Jobs dashboards).
    ``lsoa`` — Lower Super Output Area (Neighbourhoods dashboard).

    Breakdown dimension
    -------------------
    ``breakdown_category`` is ``""`` for aggregate (non-breakdown) indicators.
    For sector or category breakdowns it holds the label, e.g.
    ``"Manufacturing"``.  Using an empty string rather than NULL ensures the
    unique index behaves correctly across all PostgreSQL versions.

    Upsert key: ``(indicator_id, geography_code, reference_period, breakdown_category)``.
    """

    __tablename__ = "indicator"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    indicator_id: Mapped[str] = mapped_column(String(100), nullable=False)
    """Short machine-readable identifier, e.g. ``"employment_rate"``."""

    indicator_name: Mapped[str] = mapped_column(String(255), nullable=False)
    """Human-readable display name."""

    # --- Geography ---------------------------------------------------------

    geography_code: Mapped[str] = mapped_column(String(9), nullable=False)
    """ONS GSS code for the specific geography of this row (LAD, MSOA, or LSOA)."""

    geography_name: Mapped[str] = mapped_column(String(100), nullable=False)
    """Human-readable name of the specific geography."""

    geography_level: Mapped[str] = mapped_column(String(10), nullable=False)
    """Hierarchy level: ``'lad'``, ``'msoa'``, or ``'lsoa'``."""

    lad_code: Mapped[str] = mapped_column(String(9), nullable=False)
    """Parent LAD GSS code — for roll-up queries across all geography levels.
    Equals ``geography_code`` for LAD-level rows."""

    lad_name: Mapped[str] = mapped_column(String(100), nullable=False)
    """Parent LAD name. Equals ``geography_name`` for LAD-level rows."""

    # --- Observation -------------------------------------------------------

    reference_period: Mapped[date] = mapped_column(Date, nullable=False)
    """The date the observation relates to (first day of the period)."""

    value: Mapped[float | None] = mapped_column(nullable=True)
    """Numeric value. ``NULL`` when suppressed for disclosure control."""

    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    """Unit of measurement, e.g. ``"%"`` or ``"£"``."""

    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    """Source system identifier, e.g. ``"nomis"`` or ``"fingertips"``."""

    dataset_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    """Dataset / series code within the source system."""

    # --- Breakdown dimension -----------------------------------------------

    breakdown_category: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="''"
    )
    """Sector or category label for breakdown indicators (e.g. ``"Manufacturing"``).
    Empty string for non-breakdown (aggregate) indicators."""

    # --- Forecast ----------------------------------------------------------

    is_forecast: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default="false")
    """``True`` for model-generated forecast values; ``False`` for actuals."""

    forecast_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    """Name of the forecasting model, populated when ``is_forecast`` is ``True``."""

    # --- Audit -------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index(
            "ix_indicator_upsert_key",
            "indicator_id",
            "geography_code",
            "reference_period",
            "breakdown_category",
            unique=True,
        ),
        Index("ix_indicator_lad_code", "lad_code"),
        Index("ix_indicator_geography_level", "geography_level"),
    )


class DatasetMetadata(Base):
    """Audit record for each extraction / load run.

    One row is written per flow run, capturing provenance information so
    analysts can trace any observation back to the exact source request.
    """

    __tablename__ = "dataset_metadata"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    dataset_code: Mapped[str] = mapped_column(String(100), nullable=False)
    """Identifier matching ``Indicator.dataset_code``."""

    source: Mapped[str] = mapped_column(String(100), nullable=False)
    """Source system, e.g. ``"nomis"``."""

    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        Enum(ExtractionStatus, native_enum=False, length=20),
        nullable=False,
        default=ExtractionStatus.PENDING,
    )
    """Current lifecycle state of this extraction run."""

    prefect_flow_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    """UUID of the Prefect flow run, for cross-referencing in the Prefect UI."""

    rows_extracted: Mapped[int | None] = mapped_column(nullable=True)
    rows_loaded: Mapped[int | None] = mapped_column(nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Truncated exception message on failure."""

    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    """API endpoint or file URL that was fetched."""

    extracted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    loaded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class JobsLsoa(Base):
    """LSOA-level employee counts by SIC code, for the Jobs dashboard.

    Source: ONS Inter-Departmental Business Register (IDBR), preprocessed by
    the YHODA team (``yvj_jps_yorkshireandhumber_v1_8.csv``).

    Granularity: LSOA x Year x SIC code.
    Upsert key: ``(lsoa_code, year, sic_code)``.
    """

    __tablename__ = "jobs_lsoa"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # --- Geography ---------------------------------------------------------

    lsoa_code: Mapped[str] = mapped_column(String(9), nullable=False)
    """LSOA 2011 GSS code, e.g. ``"E01007434"``."""

    lsoa_name: Mapped[str] = mapped_column(String(100), nullable=False)

    msoa_code: Mapped[str] = mapped_column(String(9), nullable=False)
    """Parent MSOA GSS code, e.g. ``"E02006868"``."""

    msoa_name: Mapped[str] = mapped_column(String(100), nullable=False)
    """ONS-assigned MSOA name."""

    msoa_hcl_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    """Human-coded local name for the MSOA area (may differ from ONS name)."""

    lad_code: Mapped[str] = mapped_column(String(9), nullable=False)
    lad_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # --- Time --------------------------------------------------------------

    year: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- SIC hierarchy -----------------------------------------------------

    sic_code: Mapped[int] = mapped_column(Integer, nullable=False)
    """Numeric SIC 2007 code, e.g. ``1629``."""

    sic_description: Mapped[str] = mapped_column(String(500), nullable=False)
    """Full SIC description text, e.g. "Support activities for animal production…"."""

    section: Mapped[str] = mapped_column(String(200), nullable=False)
    """SIC Section letter label, e.g. "Agriculture, forestry and fishing"."""

    division: Mapped[str] = mapped_column(String(200), nullable=False)
    """SIC Division label."""

    group_name: Mapped[str] = mapped_column(String(200), nullable=False)
    """SIC Group label."""

    # --- Value -------------------------------------------------------------

    employees: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """Employee count; ``NULL`` when suppressed for disclosure control."""

    # --- Audit -------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_jobs_lsoa_upsert_key", "lsoa_code", "year", "sic_code", unique=True),
        Index("ix_jobs_lsoa_msoa_code", "msoa_code"),
        Index("ix_jobs_lsoa_lad_code", "lad_code"),
        Index("ix_jobs_lsoa_year", "year"),
    )


class IndustryBusiness(Base):
    """MSOA-level business counts by industry and turnover band, for the Industry dashboard.

    Source: ONS Inter-Departmental Business Register (IDBR), preprocessed by
    the YHODA team (``yvi_allyh_v1_6.csv``).

    Granularity: Year x MSOA x industry x turnover band.
    Upsert key: ``(year, msoa_code, industry, turnover_band)``.
    """

    __tablename__ = "industry_business"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    year: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- Geography ---------------------------------------------------------

    msoa_code: Mapped[str] = mapped_column(String(9), nullable=False)
    msoa_name: Mapped[str] = mapped_column(String(100), nullable=False)
    lad_code: Mapped[str] = mapped_column(String(9), nullable=False)
    lad_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # --- Breakdown dimensions ----------------------------------------------

    industry: Mapped[str] = mapped_column(String(200), nullable=False)
    """SIC section label, e.g. ``"Manufacturing"``."""

    turnover_band: Mapped[str] = mapped_column(String(50), nullable=False)
    """Fine-grained turnover band, e.g. ``"Micro under 250k"``."""

    # --- Value -------------------------------------------------------------

    business_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """Number of businesses; ``NULL`` when suppressed for disclosure control."""

    # --- Audit -------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index(
            "ix_industry_business_upsert_key",
            "year",
            "msoa_code",
            "industry",
            "turnover_band",
            unique=True,
        ),
        Index("ix_industry_business_lad_code", "lad_code"),
        Index("ix_industry_business_year", "year"),
    )


class IndustryBusinessKpi(Base):
    """Pre-aggregated business count KPIs with 3-year and 8-year change metrics.

    Source: Yorkshire Vitality Industry KPI preprocessed CSV
    (``yvi_allyh_v1_6_kpis_8.csv``).

    Supports Yorkshire-wide, LAD-level, and MSOA-level aggregates in one table
    via the ``grouping_level`` discriminator.

    For ``grouping_level = 'yorkshire'``, ``lad_code`` and ``msoa_code`` are
    empty strings.  For ``grouping_level = 'lad'``, ``msoa_code`` is ``''``.
    Empty strings rather than NULL keep the unique index deterministic.

    Upsert key:
        ``(grouping_level, year, lad_code, msoa_code, industry, turnover_band)``
    """

    __tablename__ = "industry_business_kpi"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    grouping_level: Mapped[str] = mapped_column(String(50), nullable=False)
    """Aggregation level: ``'yorkshire'``, ``'lad'``, or ``'msoa'``."""

    year: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- Geography — '' for higher-level aggregates ------------------------

    lad_code: Mapped[str] = mapped_column(String(9), nullable=False, server_default="''")
    lad_name: Mapped[str] = mapped_column(String(100), nullable=False, server_default="''")
    msoa_code: Mapped[str] = mapped_column(String(9), nullable=False, server_default="''")
    msoa_name: Mapped[str] = mapped_column(String(100), nullable=False, server_default="''")

    # --- Breakdown — '' when not applicable --------------------------------

    industry: Mapped[str] = mapped_column(String(200), nullable=False, server_default="''")
    turnover_band: Mapped[str] = mapped_column(String(50), nullable=False)

    # --- KPI values --------------------------------------------------------

    business_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    business_lag3: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """Business count 3 years prior (for 3-year change KPI)."""
    pct_change_3y: Mapped[float | None] = mapped_column(Float, nullable=True)
    """Percentage change in business count over 3 years."""
    business_lag8: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """Business count 8 years prior (for 8-year change KPI)."""
    pct_change_8y: Mapped[float | None] = mapped_column(Float, nullable=True)
    """Percentage change in business count over 8 years."""

    # --- Audit -------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index(
            "ix_industry_kpi_upsert_key",
            "grouping_level",
            "year",
            "lad_code",
            "msoa_code",
            "industry",
            "turnover_band",
            unique=True,
        ),
        Index("ix_industry_kpi_lad_code", "lad_code"),
        Index("ix_industry_kpi_year", "year"),
    )


class GeoLookup(Base):
    """ONS geography hierarchy: LSOA → MSOA → LAD → Region.

    Populated once from the ONS Open Geography Portal and used by transform
    tasks to aggregate sub-LAD data up to LAD level.

    Primary key is the LSOA code (unique in the ONS hierarchy).
    """

    __tablename__ = "geo_lookup"

    lsoa_code: Mapped[str] = mapped_column(String(9), primary_key=True)
    """Lower Super Output Area GSS code, e.g. ``"E01000001"``."""

    lsoa_name: Mapped[str] = mapped_column(String(100), nullable=False)

    msoa_code: Mapped[str] = mapped_column(String(9), nullable=False)
    """Middle Super Output Area GSS code, e.g. ``"E02000001"``."""

    msoa_name: Mapped[str] = mapped_column(String(100), nullable=False)

    lad_code: Mapped[str] = mapped_column(String(9), nullable=False)
    """Local Authority District GSS code, e.g. ``"E08000032"``."""

    lad_name: Mapped[str] = mapped_column(String(100), nullable=False)

    region_code: Mapped[str | None] = mapped_column(String(9), nullable=True)
    """ONS region GSS code, e.g. ``"E12000003"`` (Yorkshire & The Humber)."""

    region_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_geo_lookup_lad_code", "lad_code"),
        Index("ix_geo_lookup_msoa_code", "msoa_code"),
    )
