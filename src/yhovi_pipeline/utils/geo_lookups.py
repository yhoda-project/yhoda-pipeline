"""Geography lookup utilities.

Helpers for loading and caching the ONS geography hierarchy from the
``GeoLookup`` table, used by transform tasks.
"""

from __future__ import annotations

import functools

import pandas as pd
from sqlalchemy import create_engine, text

from yhovi_pipeline.config import get_settings


@functools.lru_cache(maxsize=1)
def get_geo_lookup() -> pd.DataFrame:
    """Load the full LSOA → MSOA → LAD → Region lookup into a DataFrame.

    The result is cached in memory for the duration of the process so that
    multiple tasks in the same flow run do not re-query the database.

    Returns:
        DataFrame with columns: ``lsoa_code``, ``lsoa_name``, ``msoa_code``,
        ``msoa_name``, ``lad_code``, ``lad_name``, ``region_code``, ``region_name``.
    """
    settings = get_settings()
    engine = create_engine(settings.database_url.get_secret_value())

    with engine.connect() as conn:
        df = pd.read_sql(
            text(
                "SELECT lsoa_code, lsoa_name, msoa_code, msoa_name, lad_code, lad_name, region_code, region_name FROM geo_lookup"
            ),
            conn,
        )

    return df


def lsoa_to_lad(lsoa_code: str) -> str | None:
    """Look up the LAD code for a given LSOA code.

    Args:
        lsoa_code: The LSOA GSS code to look up.

    Returns:
        The corresponding LAD GSS code, or ``None`` if not found.
    """
    lookup = get_geo_lookup()
    match = lookup.loc[lookup["lsoa_code"] == lsoa_code, "lad_code"]
    return match.iloc[0] if not match.empty else None
