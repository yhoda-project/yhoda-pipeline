"""PostgreSQL load tasks.

Writes normalised ``Indicator`` rows to the PostgreSQL data warehouse using
an idempotent upsert strategy (INSERT … ON CONFLICT UPDATE).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
from prefect import task
from prefect.logging import get_run_logger
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from yhovi_pipeline.config import get_settings
from yhovi_pipeline.db.models import DatasetMetadata, ExtractionStatus, Indicator


def _get_engine() -> Engine:
    """Create a SQLAlchemy engine from settings."""
    settings = get_settings()
    return create_engine(settings.database_url.get_secret_value())


@task(
    name="load/database/upsert-indicators",
    description="Upsert a normalised Indicator DataFrame into the PostgreSQL data warehouse.",
)
def upsert_indicators(df: pd.DataFrame, dataset_code: str) -> int:
    """Upsert rows into the ``indicator`` table.

    Uses the unique index on
    ``(indicator_id, geography_code, reference_period, breakdown_category)``
    as the merge key.  Existing rows are updated; new rows are inserted.

    Args:
        df: Normalised DataFrame with columns matching the ``Indicator``
            schema: indicator_id, indicator_name, geography_code,
            geography_name, geography_level, lad_code, lad_name,
            reference_period, value, unit, source, dataset_code,
            breakdown_category, is_forecast, forecast_model.
        dataset_code: Dataset identifier for logging.

    Returns:
        Number of rows upserted.
    """
    logger = get_run_logger()
    engine = _get_engine()

    records = df.to_dict(orient="records")
    if not records:
        logger.warning("No records to upsert for %s", dataset_code)
        return 0

    now = datetime.now(UTC)
    for rec in records:
        rec.setdefault("created_at", now)
        rec["updated_at"] = now

    stmt = pg_insert(Indicator).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=[
            "indicator_id",
            "geography_code",
            "reference_period",
            "breakdown_category",
        ],
        set_={
            "indicator_name": stmt.excluded.indicator_name,
            "geography_name": stmt.excluded.geography_name,
            "geography_level": stmt.excluded.geography_level,
            "lad_code": stmt.excluded.lad_code,
            "lad_name": stmt.excluded.lad_name,
            "value": stmt.excluded.value,
            "unit": stmt.excluded.unit,
            "source": stmt.excluded.source,
            "dataset_code": stmt.excluded.dataset_code,
            "subdomain": stmt.excluded.subdomain,
            "is_forecast": stmt.excluded.is_forecast,
            "forecast_model": stmt.excluded.forecast_model,
            "updated_at": stmt.excluded.updated_at,
        },
    )

    with engine.begin() as conn:
        conn.execute(stmt)

    logger.info("Upserted %d rows for dataset %s", len(records), dataset_code)
    return len(records)


@task(
    name="load/database/write-metadata",
    description="Write a DatasetMetadata audit record to the data warehouse.",
)
def write_metadata(
    dataset_code: str,
    source: str,
    status: ExtractionStatus,
    prefect_flow_run_id: str | None = None,
    rows_extracted: int | None = None,
    rows_loaded: int | None = None,
    error_message: str | None = None,
    source_url: str | None = None,
) -> None:
    """Insert an audit record into the ``dataset_metadata`` table.

    Args:
        dataset_code: Dataset identifier.
        source: Source system identifier.
        status: Final ``ExtractionStatus`` for this run.
        prefect_flow_run_id: UUID of the Prefect flow run, if available.
        rows_extracted: Number of rows returned by the extract step.
        rows_loaded: Number of rows written to the warehouse.
        error_message: Truncated exception message on failure.
        source_url: API endpoint or file URL that was fetched.
    """
    logger = get_run_logger()
    engine = _get_engine()

    now = datetime.now(UTC)
    record = DatasetMetadata(
        dataset_code=dataset_code,
        source=source,
        extraction_status=status,
        prefect_flow_run_id=prefect_flow_run_id,
        rows_extracted=rows_extracted,
        rows_loaded=rows_loaded,
        error_message=error_message,
        source_url=source_url,
        extracted_at=now if status == ExtractionStatus.SUCCESS else None,
        loaded_at=now if rows_loaded else None,
        created_at=now,
    )

    with Session(engine) as session:
        session.add(record)
        session.commit()

    logger.info("Wrote metadata for %s: %s", dataset_code, status.value)


@task(
    name="load/database/query-population",
    description="Fetch total population by LAD and year from the indicator table.",
)
def query_population() -> pd.DataFrame:
    """Query total population estimates from the indicator table.

    Used by DWP normalisation to compute per-capita rates.

    Returns:
        DataFrame with columns: lad_code (str), year (int), population (float).
    """
    logger = get_run_logger()
    engine = _get_engine()

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT lad_code, EXTRACT(YEAR FROM reference_period)::int AS year, "
                "value AS population "
                "FROM indicator "
                "WHERE indicator_id = 'total_population'"
            )
        ).fetchall()

    df = pd.DataFrame(rows, columns=["lad_code", "year", "population"])

    if df.empty:
        logger.warning("No population data found - load SDPOP before running DWP flows")
    else:
        logger.info("Loaded population for %d LAD-year combinations", len(df))

    return df
