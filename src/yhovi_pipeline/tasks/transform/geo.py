"""Geo aggregation transform tasks.

Aggregates sub-LAD data (LSOA / MSOA level) up to LAD level using the
``GeoLookup`` table.
"""

from __future__ import annotations

import pandas as pd
from prefect import task

from yhovi_pipeline.utils.geo_lookups import get_geo_lookup


@task(
    name="transform/geo/aggregate-to-lad",
    description="Aggregate sub-LAD data to LAD level using the ONS geo lookup.",
)
def aggregate_to_lad(
    df: pd.DataFrame,
    value_col: str,
    geo_col: str = "lsoa_code",
    agg: str = "mean",
) -> pd.DataFrame:
    """Join sub-LAD data to the geo lookup and aggregate to LAD level.

    Args:
        df: Input DataFrame with sub-LAD rows.
        value_col: Name of the numeric column to aggregate.
        geo_col: Name of the geography code column in ``df``.
            Supported values: ``"lsoa_code"`` (default), ``"msoa_code"``.
        agg: Aggregation function passed to ``groupby.agg``.
            Use ``"mean"`` for rates/scores, ``"sum"`` for counts.

    Returns:
        DataFrame with columns ``[lad_code, lad_name, value]`` aggregated to
        LAD level.

    Raises:
        ValueError: If ``geo_col`` is not ``"lsoa_code"`` or ``"msoa_code"``.
    """
    lookup = get_geo_lookup()

    if geo_col == "lsoa_code":
        join_cols = lookup[["lsoa_code", "lad_code", "lad_name"]]
        merged = df.merge(join_cols, on="lsoa_code", how="left")
    elif geo_col == "msoa_code":
        join_cols = lookup[["msoa_code", "lad_code", "lad_name"]].drop_duplicates("msoa_code")
        merged = df.merge(join_cols, on="msoa_code", how="left")
    else:
        raise ValueError(f"Unsupported geo_col: {geo_col!r}. Expected 'lsoa_code' or 'msoa_code'.")

    result = (
        merged.groupby(["lad_code", "lad_name"], as_index=False)[value_col]
        .agg(agg)
        .rename(columns={value_col: "value"})
    )
    return result
