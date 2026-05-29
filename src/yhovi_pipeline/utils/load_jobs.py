"""Load the Jobs dashboard CSV into the jobs_lsoa table.

Source: yvj_jps_yorkshireandhumber_v1_8.csv
CSV columns: LSOA11CD, Year, SIC, Employees, LSOA11NM, MSOA_Code, MSOA11NM,
             Area..MSOA., LAD_Code, Local.Authority, SIC_Code, Section,
             Division, Group

Usage (from VM)::

    export $(grep -v '^#' .env | xargs)
    uv run python -m yhovi_pipeline.utils.load_jobs
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

from yhovi_pipeline.config import YORKSHIRE_LAD_CODES, get_settings
from yhovi_pipeline.db.models import JobsLsoa

_BATCH_SIZE = 3_000  # psycopg2 limit: 65535 params; 3000 rows x 15 cols = 45000

JOBS_CSV = "/mnt/yhoda_drive/Shared/3_Yorkshire_Vitality_Jobs/yvj_jps_yorkshireandhumber_v1_8.csv"


def load_jobs(path: str = JOBS_CSV) -> int:
    """Load the LSOA-level Jobs CSV into the ``jobs_lsoa`` table.

    Filters to Yorkshire LADs, then upserts on ``(lsoa_code, year, sic_code)``.

    Args:
        path: Path to the source CSV file.

    Returns:
        Number of rows upserted.
    """
    settings = get_settings()
    engine = create_engine(settings.database_url.get_secret_value())

    print(f"Reading {path}...")
    df = pd.read_csv(path, low_memory=False)

    df = df[df["LAD_Code"].isin(YORKSHIRE_LAD_CODES)].copy()
    if df.empty:
        print("  No rows matched Yorkshire LAD codes.")
        return 0

    now = datetime.now(UTC)

    # Build result DataFrame using vectorised operations
    employees = pd.to_numeric(df["Employees"], errors="coerce")

    result = pd.DataFrame(
        {
            "lsoa_code": df["LSOA11CD"].astype(str),
            "lsoa_name": df["LSOA11NM"].astype(str),
            "msoa_code": df["MSOA_Code"].astype(str),
            "msoa_name": df["MSOA11NM"].astype(str),
            "msoa_hcl_name": df["Area..MSOA."].where(df["Area..MSOA."].notna(), None),
            "lad_code": df["LAD_Code"].astype(str),
            "lad_name": df["Local.Authority"].astype(str),
            "year": df["Year"].astype(int),
            "sic_code": df["SIC_Code"].astype(int),
            "sic_description": df["SIC"].astype(str),
            "section": df["Section"].astype(str),
            "division": df["Division"].astype(str),
            "group_name": df["Group"].astype(str),
            # Convert NaN → None so SQLAlchemy sends SQL NULL
            "employees": employees.where(employees.notna(), None),
            "created_at": now,
            "updated_at": now,
        }
    )

    # pandas object columns holding Python None are fine; float NaN must be None
    result["employees"] = result["employees"].apply(
        lambda x: int(x) if x is not None and pd.notna(x) else None
    )

    records = result.to_dict(orient="records")

    with engine.begin() as conn:
        for i in range(0, len(records), _BATCH_SIZE):
            batch = records[i : i + _BATCH_SIZE]
            stmt = pg_insert(JobsLsoa).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["lsoa_code", "year", "sic_code"],
                set_={
                    "lsoa_name": stmt.excluded.lsoa_name,
                    "msoa_code": stmt.excluded.msoa_code,
                    "msoa_name": stmt.excluded.msoa_name,
                    "msoa_hcl_name": stmt.excluded.msoa_hcl_name,
                    "lad_code": stmt.excluded.lad_code,
                    "lad_name": stmt.excluded.lad_name,
                    "sic_description": stmt.excluded.sic_description,
                    "section": stmt.excluded.section,
                    "division": stmt.excluded.division,
                    "group_name": stmt.excluded.group_name,
                    "employees": stmt.excluded.employees,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            conn.execute(stmt)

    print(f"  Upserted {len(records)} rows into jobs_lsoa.")
    return len(records)


if __name__ == "__main__":
    count = load_jobs()
    print(f"Done. Total rows upserted: {count}")
