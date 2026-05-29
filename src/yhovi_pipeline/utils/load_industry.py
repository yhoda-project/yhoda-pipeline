"""Load the Industry dashboard CSVs into industry_business and industry_business_kpi.

Sources (in /mnt/yhoda_drive/Shared/2_Yorkshire_Vitality_by_Industry/):
  yvi_allyh_v1_6.csv          → industry_business (MSOA-level granular rows)
  yvi_allyh_v1_6_kpis_8.csv  → industry_business_kpi (pre-aggregated KPIs)

Expected columns in yvi_allyh_v1_6.csv:
  Year, Industry, MSOA, Turnover, Business, MSOA11NM, msoa11hclnm, LAD23NM
  (all rows are MSOA-level; there is no Grouping_Level column)

Expected columns in yvi_allyh_v1_6_kpis_8.csv:
  Grouping_Level, Year, LAD23NM, MSOA, Turnover, Industry,
  Business, Business_Lag3, Pct_Change_3Y, Business_Lag8, Pct_Change_8Y

NOTE: If the actual column names differ from those above, update the
``_GRANULAR_COLS`` and ``_KPI_COLS`` mappings at the top of this file.
The loader prints each CSV's actual columns at startup so you can verify.

Usage (from VM)::

    export $(grep -v '^#' .env | xargs)
    uv run python -m yhovi_pipeline.utils.load_industry
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

from yhovi_pipeline.config import YORKSHIRE_LAD_CODES, get_settings
from yhovi_pipeline.db.models import IndustryBusiness, IndustryBusinessKpi
from yhovi_pipeline.utils.geo_lookups import get_geo_lookup

_BATCH_SIZE = 3_000  # psycopg2 limit: 65535 params; 3000 rows x 15 cols = 45000

INDUSTRY_BASE = "/mnt/yhoda_drive/Shared/2_Yorkshire_Vitality_by_Industry"
GRANULAR_CSV = f"{INDUSTRY_BASE}/yvi_allyh_v1_6.csv"
KPI_CSV = f"{INDUSTRY_BASE}/yvi_allyh_v1_6_kpis_8.csv"

# ---------------------------------------------------------------------------
# Column mappings — update these if the CSV headers change between versions.
# key = our internal name, value = actual CSV column name.
# ---------------------------------------------------------------------------

_GRANULAR_COLS: dict[str, str] = {
    "msoa_code": "MSOA",
    "msoa_name": "MSOA11NM",
    "lad_name": "LAD23NM",
    "industry": "Industry",
    "turnover_band": "Turnover",
    "year": "Year",
    "business_count": "Business",
}

_KPI_COLS: dict[str, str] = {
    "grouping_level": "Grouping_Level",
    "year": "Year",
    "lad_name": "LAD23NM",
    "msoa": "MSOA",  # may be a code or a name; '' / NaN for Yorkshire/LAD rows
    "industry": "Industry",
    "turnover_band": "Turnover",
    "business_count": "Business",
    "business_lag3": "Business_Lag3",
    "pct_change_3y": "Pct_Change_3Y",
    "business_lag8": "Business_Lag8",
    "pct_change_8y": "Pct_Change_8Y",
}


def _is_gss_code(series: pd.Series) -> bool:
    """Return True if the non-null values look like GSS codes (e.g. ``E02006868``)."""
    sample = series.dropna().astype(str)
    if sample.empty:
        return False
    return bool(sample.str.match(r"^[EW]\d{8}$").all())


def _build_msoa_lad_lookup() -> pd.DataFrame:
    """Return a DataFrame mapping msoa_code → lad_code, lad_name, msoa_name."""
    geo = get_geo_lookup()
    return geo.groupby("msoa_code")[["lad_code", "lad_name", "msoa_name"]].first().reset_index()


def _normalise_grouping_level(val: str) -> str:
    """Normalise Grouping_Level values to lowercase identifiers."""
    return str(val).strip().lower().replace(" ", "_")


def load_industry_business(path: str = GRANULAR_CSV) -> int:
    """Load the MSOA-level Industry CSV into ``industry_business``.

    All rows are at MSOA level (no Grouping_Level column).  The MSOA column
    contains GSS codes; lad_code is resolved via geo_lookup; lad_name is
    taken directly from LAD23NM.

    Args:
        path: Path to the granular CSV file.

    Returns:
        Number of rows upserted.
    """
    settings = get_settings()
    engine = create_engine(settings.database_url.get_secret_value())

    print(f"Reading {path}...")
    df = pd.read_csv(path, low_memory=False)
    print(f"  Columns: {list(df.columns)}")

    c = _GRANULAR_COLS

    # Resolve MSOA code → lad_code via geo_lookup
    msoa_lookup = _build_msoa_lad_lookup()[["msoa_code", "lad_code"]]
    df = df.merge(msoa_lookup, left_on=c["msoa_code"], right_on="msoa_code", how="left")

    missing = df["lad_code"].isna().sum()
    if missing:
        print(f"  WARNING: {missing} MSOA codes not in geo_lookup - skipped.")
    df = df.dropna(subset=["lad_code"]).copy()

    # Filter to Yorkshire LADs
    df = df[df["lad_code"].isin(YORKSHIRE_LAD_CODES)].copy()
    if df.empty:
        print("  No rows matched Yorkshire LAD codes.")
        return 0

    now = datetime.now(UTC)
    business = pd.to_numeric(df[c["business_count"]], errors="coerce")

    result = pd.DataFrame(
        {
            "year": df[c["year"]].astype(int),
            "msoa_code": df[c["msoa_code"]].astype(str),
            "msoa_name": df[c["msoa_name"]].astype(str),
            "lad_code": df["lad_code"].astype(str),
            "lad_name": df[c["lad_name"]].astype(str),
            "industry": df[c["industry"]].fillna("").astype(str),
            "turnover_band": df[c["turnover_band"]].astype(str),
            "business_count": business.where(business.notna(), None),
            "created_at": now,
            "updated_at": now,
        }
    )
    result["business_count"] = result["business_count"].apply(
        lambda x: int(x) if x is not None and pd.notna(x) else None
    )

    records = result.to_dict(orient="records")

    with engine.begin() as conn:
        for i in range(0, len(records), _BATCH_SIZE):
            batch = records[i : i + _BATCH_SIZE]
            stmt = pg_insert(IndustryBusiness).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["year", "msoa_code", "industry", "turnover_band"],
                set_={
                    "msoa_name": stmt.excluded.msoa_name,
                    "lad_code": stmt.excluded.lad_code,
                    "lad_name": stmt.excluded.lad_name,
                    "business_count": stmt.excluded.business_count,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            conn.execute(stmt)

    print(f"  Upserted {len(records)} rows into industry_business.")
    return len(records)


def load_industry_kpi(path: str = KPI_CSV) -> int:
    """Load the pre-aggregated KPI CSV into ``industry_business_kpi``.

    All grouping levels (yorkshire, lad, msoa) are loaded.  Geography
    columns are normalised: empty string for levels above the row's
    grouping level.

    Args:
        path: Path to the KPI CSV file.

    Returns:
        Number of rows upserted.
    """
    settings = get_settings()
    engine = create_engine(settings.database_url.get_secret_value())

    print(f"Reading {path}...")
    df = pd.read_csv(path, low_memory=False)
    print(f"  Columns: {list(df.columns)}")

    c = _KPI_COLS

    now = datetime.now(UTC)

    # Build MSOA code/name series — may be empty for LAD/Yorkshire rows
    msoa_col = df[c["msoa"]].fillna("").astype(str).str.strip()
    if _is_gss_code(msoa_col[msoa_col != ""]):
        lad_lookup = (
            get_geo_lookup()
            .groupby("msoa_code")[["lad_code", "lad_name", "msoa_name"]]
            .first()
            .reset_index()
        )
        # Store CSV lad_name before merge to use as fallback (avoids index misalignment)
        df = df.copy()
        df["_lad_name_csv"] = df[c["lad_name"]].fillna("").values
        merged = df.merge(
            lad_lookup,
            left_on=c["msoa"],
            right_on="msoa_code",
            how="left",
        )
        lad_code_series = merged["lad_code"].fillna("").astype(str)
        lad_name_series = merged["lad_name"].fillna(merged["_lad_name_csv"]).astype(str)
        msoa_code_series = merged["msoa_code"].fillna("").astype(str)
        msoa_name_series = merged["msoa_name"].fillna("").astype(str)
    else:
        # MSOA column is a name — use LAD name from CSV; lookup lad_code by name
        lad_name_to_code = get_geo_lookup().groupby("lad_name")["lad_code"].first()
        lad_code_series = df[c["lad_name"]].fillna("").map(lad_name_to_code).fillna("").astype(str)
        lad_name_series = df[c["lad_name"]].fillna("").astype(str)
        msoa_code_series = msoa_col
        msoa_name_series = msoa_col

    def _to_int_or_none(series: pd.Series) -> list[int | None]:
        numeric = pd.to_numeric(series, errors="coerce")
        return [int(x) if pd.notna(x) else None for x in numeric]

    def _to_float_or_none(series: pd.Series) -> list[float | None]:
        numeric = pd.to_numeric(series, errors="coerce")
        return [float(x) if pd.notna(x) else None for x in numeric]

    result = pd.DataFrame(
        {
            "grouping_level": df[c["grouping_level"]].apply(_normalise_grouping_level),
            "year": df[c["year"]].astype(int),
            "lad_code": lad_code_series,
            "lad_name": lad_name_series,
            "msoa_code": msoa_code_series,
            "msoa_name": msoa_name_series,
            "industry": df[c["industry"]].fillna("").astype(str),
            "turnover_band": df[c["turnover_band"]].astype(str),
            "business_count": _to_int_or_none(df[c["business_count"]]),
            "business_lag3": _to_int_or_none(df[c["business_lag3"]]),
            "pct_change_3y": _to_float_or_none(df[c["pct_change_3y"]]),
            "business_lag8": _to_int_or_none(df[c["business_lag8"]]),
            "pct_change_8y": _to_float_or_none(df[c["pct_change_8y"]]),
            "created_at": now,
            "updated_at": now,
        }
    )

    # Drop duplicates on the upsert key — the CSV contains duplicate rows and
    # ON CONFLICT DO UPDATE cannot affect the same row twice in one statement.
    result = result.drop_duplicates(
        subset=["grouping_level", "year", "lad_code", "msoa_code", "industry", "turnover_band"],
        keep="last",
    )

    records = result.to_dict(orient="records")
    # pandas stores int+None columns as float64, so to_dict() emits float nan
    # instead of None. PostgreSQL raises "integer out of range" when it tries
    # to cast nan::float -> integer. Fix inline on the dict (v != v is True
    # only for IEEE 754 NaN, safe for any Python float).
    for r in records:
        for col in ("business_count", "business_lag3", "business_lag8"):
            v = r[col]
            r[col] = None if (v is None or (isinstance(v, float) and v != v)) else int(v)

    with engine.begin() as conn:
        for i in range(0, len(records), _BATCH_SIZE):
            batch = records[i : i + _BATCH_SIZE]
            stmt = pg_insert(IndustryBusinessKpi).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=[
                    "grouping_level",
                    "year",
                    "lad_code",
                    "msoa_code",
                    "industry",
                    "turnover_band",
                ],
                set_={
                    "lad_name": stmt.excluded.lad_name,
                    "msoa_name": stmt.excluded.msoa_name,
                    "business_count": stmt.excluded.business_count,
                    "business_lag3": stmt.excluded.business_lag3,
                    "pct_change_3y": stmt.excluded.pct_change_3y,
                    "business_lag8": stmt.excluded.business_lag8,
                    "pct_change_8y": stmt.excluded.pct_change_8y,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            conn.execute(stmt)

    print(f"  Upserted {len(records)} rows into industry_business_kpi.")
    return len(records)


def load_all_industry() -> None:
    """Load both Industry CSVs in sequence."""
    total = 0
    total += load_industry_business()
    total += load_industry_kpi()
    print(f"\nDone. Total rows upserted: {total}")


if __name__ == "__main__":
    load_all_industry()
