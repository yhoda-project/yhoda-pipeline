"""Seed the geo_lookup table from the ONS OA→LSOA→MSOA→LAD lookup CSV.

Reads the preprocessed file from the shared drive, deduplicates to one row
per LSOA (the CSV is OA-level), filters to Yorkshire LADs, and upserts into
the geo_lookup table.

Usage (from the VM)::

    export $(grep -v '^#' .env | xargs)
    uv run python -m yhovi_pipeline.utils.seed_geo_lookup
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

from yhovi_pipeline.config import YORKSHIRE_LAD_CODES, get_settings
from yhovi_pipeline.db.models import GeoLookup

GEO_CSV_PATH = (
    "/mnt/yhoda_drive/Shared/1_Yorkshire_Vitality_Observatory"
    "/data_preprocessing/OA_LSOA_MSOA_LAD/OA_LSOA_MSOA_LAD_v1_5.csv"
)


def load_geo_lookup(path: str = GEO_CSV_PATH) -> int:
    """Seed the geo_lookup table from the ONS geography CSV.

    Args:
        path: Path to the OA_LSOA_MSOA_LAD CSV file.

    Returns:
        Number of rows upserted.
    """
    settings = get_settings()
    engine = create_engine(settings.database_url.get_secret_value())

    df = pd.read_csv(
        path, usecols=["LSOA21CD", "LSOA21NM", "MSOA21CD", "MSOA21NM", "LAD23CD", "LAD23NM"]
    )

    # Filter to Yorkshire LADs only
    df = df[df["LAD23CD"].isin(YORKSHIRE_LAD_CODES)]

    # CSV is OA-level; deduplicate to one row per LSOA
    df = df.drop_duplicates(subset=["LSOA21CD"])

    records = [
        {
            "lsoa_code": row["LSOA21CD"],
            "lsoa_name": row["LSOA21NM"],
            "msoa_code": row["MSOA21CD"],
            "msoa_name": row["MSOA21NM"],
            "lad_code": row["LAD23CD"],
            "lad_name": row["LAD23NM"],
            "region_code": None,
            "region_name": None,
        }
        for _, row in df.iterrows()
    ]

    if not records:
        print("No Yorkshire LSOAs found — check LAD codes in CSV.")
        return 0

    stmt = pg_insert(GeoLookup).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["lsoa_code"],
        set_={
            "lsoa_name": stmt.excluded.lsoa_name,
            "msoa_code": stmt.excluded.msoa_code,
            "msoa_name": stmt.excluded.msoa_name,
            "lad_code": stmt.excluded.lad_code,
            "lad_name": stmt.excluded.lad_name,
        },
    )

    with engine.begin() as conn:
        conn.execute(stmt)

    print(f"Upserted {len(records)} LSOAs into geo_lookup.")
    return len(records)


if __name__ == "__main__":
    load_geo_lookup()
