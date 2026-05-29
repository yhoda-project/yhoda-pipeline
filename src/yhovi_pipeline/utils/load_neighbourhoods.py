"""Load the Neighbourhoods dashboard CSV into the indicator table.

Source: Copy_for_Poppy1_yvn_lsoa2021_v2_1.csv
CSV columns: lsoa_name, lsoa_code, Time, Value, Indicator, Domain

Each row is an LSOA-level observation.  The loader:
  1. Parses Time (``31/12/2011`` format) into a ``date``.
  2. Joins with ``geo_lookup`` to resolve ``lad_code``/``lad_name`` for each LSOA.
  3. Filters to Yorkshire LADs.
  4. Derives ``indicator_id`` by slugifying the Indicator column (prefixed with
     ``"lsoa_"`` to avoid collision with LAD-level indicators of the same name).
  5. Upserts into the ``indicator`` table using the standard upsert key.

``Domain`` (e.g. "Demographics") is metadata used by the dashboard for
display grouping only and is not stored in the database.

Usage (from VM)::

    export $(grep -v '^#' .env | xargs)
    uv run python -m yhovi_pipeline.utils.load_neighbourhoods
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

from yhovi_pipeline.config import YORKSHIRE_LAD_CODES, get_settings
from yhovi_pipeline.db.models import Indicator
from yhovi_pipeline.utils.geo_lookups import get_geo_lookup

NEIGHBOURHOODS_CSV = (
    "/mnt/yhoda_drive/Shared/5_Yorkshire_Vitality_Neighbourhoods/"
    "Copy_for_Poppy1_yvn_lsoa2021_v2_1.csv"
)

_BATCH_SIZE = 3_000  # psycopg2 limit: 65535 params; 3000 rows x 17 cols = 51000

DATASET_CODE = "yvn_lsoa"
SOURCE = "ons"


def _slugify(text: str) -> str:
    """Convert a human-readable indicator name to a machine-readable slug.

    Example: ``"Total Population (People)"`` → ``"total_population_people"``
    """
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug


def _parse_time(time_str: str) -> date:
    """Parse ``"31/12/2011"`` (DD/MM/YYYY) into a ``date`` object."""
    day, month, year = time_str.strip().split("/")
    return date(int(year), int(month), int(day))


def load_neighbourhoods(path: str = NEIGHBOURHOODS_CSV) -> int:
    """Load the LSOA-level Neighbourhoods CSV into the ``indicator`` table.

    Args:
        path: Path to the source CSV file.

    Returns:
        Number of rows upserted.
    """
    settings = get_settings()
    engine = create_engine(settings.database_url.get_secret_value())

    print(f"Reading {path}...")
    df = pd.read_csv(path)

    # ------------------------------------------------------------------ #
    # Resolve lad_code / lad_name from geo_lookup                        #
    # ------------------------------------------------------------------ #
    geo = get_geo_lookup()[["lsoa_code", "lad_code", "lad_name"]]
    df = df.merge(geo, on="lsoa_code", how="left")

    # Warn about LSOAs missing from the lookup (boundary mismatch or data error)
    missing = df["lad_code"].isna().sum()
    if missing:
        print(f"  WARNING: {missing} rows have no geo_lookup match - they will be skipped.")
    df = df.dropna(subset=["lad_code"])

    # Filter to Yorkshire LADs
    df = df[df["lad_code"].isin(YORKSHIRE_LAD_CODES)].copy()
    if df.empty:
        print("  No rows matched Yorkshire LAD codes.")
        return 0

    # ------------------------------------------------------------------ #
    # Parse dates and build indicator IDs                                 #
    # ------------------------------------------------------------------ #
    df["reference_period"] = df["Time"].apply(_parse_time)
    df["indicator_id"] = "lsoa_" + df["Indicator"].apply(_slugify)

    now = datetime.now(UTC)
    result = pd.DataFrame(
        {
            "indicator_id": df["indicator_id"],
            "indicator_name": df["Indicator"],
            "geography_code": df["lsoa_code"].astype(str),
            "geography_name": df["lsoa_name"].astype(str),
            "geography_level": "lsoa",
            "lad_code": df["lad_code"].astype(str),
            "lad_name": df["lad_name"].astype(str),
            "reference_period": df["reference_period"],
            "value": pd.to_numeric(df["Value"], errors="coerce"),
            "unit": None,
            "source": SOURCE,
            "dataset_code": DATASET_CODE,
            "breakdown_category": "",
            "is_forecast": False,
            "forecast_model": None,
            "created_at": now,
            "updated_at": now,
        }
    )
    result = result.dropna(subset=["value"])

    records = result.to_dict(orient="records")
    if not records:
        print("  No valid records to upsert.")
        return 0

    with engine.begin() as conn:
        for i in range(0, len(records), _BATCH_SIZE):
            batch = records[i : i + _BATCH_SIZE]
            stmt = pg_insert(Indicator).values(batch)
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
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            conn.execute(stmt)

    print(f"  Upserted {len(records)} rows into indicator (geography_level='lsoa').")
    return len(records)


if __name__ == "__main__":
    count = load_neighbourhoods()
    print(f"Done. Total rows upserted: {count}")
