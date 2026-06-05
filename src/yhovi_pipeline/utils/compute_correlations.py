"""Compute Spearman correlations between all Observatory indicators and store in the
correlations table.

Reads LAD-level aggregate rows from the indicator table, filters out years 2004-2009
to match the original R analysis (yhoda_vitality_observatory_correlations_v1_3.Rmd),
computes pairwise Spearman rho and p-values using pairwise complete observations,
generates plain-English interpretation messages, and upserts all pairs to the
correlations table.

Run this after load_all() so the indicator table is fully populated.

Usage (from the VM)::

    export $(grep -v '^#' .env | xargs)
    uv run python -m yhovi_pipeline.utils.compute_correlations
"""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from yhovi_pipeline.config import get_settings
from yhovi_pipeline.db.models import Correlation

_MIN_OBSERVATIONS = 3
_EXCLUDED_YEARS = set(range(2004, 2010))


def _generate_message(rho: float, p_value: float) -> str:
    """Generate a plain-English interpretation of a Spearman correlation."""
    abs_rho = abs(rho)
    is_significant = p_value < 0.05

    if abs_rho >= 0.8:
        strength = "very strong"
    elif abs_rho >= 0.6:
        strength = "strong"
    elif abs_rho >= 0.4:
        strength = "moderate"
    elif abs_rho >= 0.2:
        strength = "weak"
    else:
        strength = "no meaningful"

    if strength == "no meaningful":
        if is_significant:
            return (
                "there is a very weak but statistically significant relationship, "
                "however, the effect is minimal."
            )
        return (
            "there is no meaningful relationship between these indicators, "
            "and the result is not statistically significant."
        )

    direction = "positive" if rho > 0 else "negative"
    trend = (
        "as one indicator increases, the other tends to increase as well."
        if rho > 0
        else "as one indicator increases, the other tends to decrease."
    )

    if is_significant:
        return (
            f"there is a {strength} and statistically significant {direction} relationship, {trend}"
        )
    return (
        f"there is a {strength} {direction} relationship, but it is not statistically "
        f"significant, the result may be due to random variation."
    )


def compute_and_store_correlations() -> int:
    """Compute all pairwise Spearman correlations and upsert to the correlations table.

    Returns:
        Number of rows upserted.
    """
    settings = get_settings()
    engine = create_engine(settings.database_url.get_secret_value())

    with engine.connect() as conn:
        df = pd.read_sql(
            text(
                """
                SELECT indicator_id, indicator_name, lad_code,
                       EXTRACT(YEAR FROM reference_period)::int AS year, value
                FROM indicator
                WHERE geography_level = 'lad'
                  AND breakdown_category = ''
                  AND value IS NOT NULL
                """
            ),
            conn,
        )

    df = df[~df["year"].isin(_EXCLUDED_YEARS)]

    name_lookup: dict[str, str] = df.groupby("indicator_id")["indicator_name"].first().to_dict()

    df_wide = df.pivot_table(
        index=["lad_code", "year"],
        columns="indicator_id",
        values="value",
        aggfunc="mean",
    )

    indicator_ids = list(df_wide.columns)
    now = datetime.now(UTC)
    records: list[dict[str, object]] = []

    for id1 in indicator_ids:
        for id2 in indicator_ids:
            x = df_wide[id1].to_numpy(dtype=float)
            y = df_wide[id2].to_numpy(dtype=float)

            mask = ~(np.isnan(x) | np.isnan(y))
            if mask.sum() < _MIN_OBSERVATIONS:
                continue

            result = stats.spearmanr(x[mask], y[mask])
            rho = float(result.statistic)
            p_value = float(result.pvalue)

            records.append(
                {
                    "indicator_1_id": id1,
                    "indicator_2_id": id2,
                    "indicator_1_name": name_lookup.get(id1, id1),
                    "indicator_2_name": name_lookup.get(id2, id2),
                    "spearman_rho": rho,
                    "p_value": p_value,
                    "is_significant": p_value < 0.05,
                    "message": _generate_message(rho, p_value),
                    "computed_at": now,
                }
            )

    if not records:
        print("No correlation pairs computed - is the indicator table populated?")
        return 0

    stmt = pg_insert(Correlation).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["indicator_1_id", "indicator_2_id"],
        set_={
            "indicator_1_name": stmt.excluded.indicator_1_name,
            "indicator_2_name": stmt.excluded.indicator_2_name,
            "spearman_rho": stmt.excluded.spearman_rho,
            "p_value": stmt.excluded.p_value,
            "is_significant": stmt.excluded.is_significant,
            "message": stmt.excluded.message,
            "computed_at": stmt.excluded.computed_at,
        },
    )

    with engine.begin() as conn:
        conn.execute(stmt)

    print(f"Upserted {len(records)} correlation pairs.")
    return len(records)


if __name__ == "__main__":
    compute_and_store_correlations()
