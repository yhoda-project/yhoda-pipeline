"""Normalisation transform tasks.

Converts source-specific DataFrames into the canonical ``Indicator`` schema
used by the load tasks.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, date, datetime

import pandas as pd
from prefect import task
from prefect.logging import get_run_logger

from yhovi_pipeline.config import YORKSHIRE_LAD_CODES

_logger = logging.getLogger(__name__)


def _get_logger() -> logging.Logger | logging.LoggerAdapter[logging.Logger]:
    try:
        return get_run_logger()
    except Exception:
        return _logger


def _parse_nomis_date(date_name: str) -> date:
    """Parse a Nomis DATE_NAME string to a date.

    Handles two formats:
    - Rolling periods: "Jan 2004-Dec 2004" — returns first day of end month.
    - Plain years: "2023" — returns 1 Jan of that year (ASHE annual data).

    Args:
        date_name: Nomis DATE_NAME value.

    Returns:
        A ``date`` representing the reference period.
    """
    # Rolling period: "Jan 2004-Dec 2004"
    match = re.search(r"-\s*(\w{3})\s+(\d{4})", date_name)
    if match:
        month_str, year_str = match.group(1), match.group(2)
        return datetime.strptime(f"01 {month_str} {year_str}", "%d %b %Y").date()

    # Plain year: "2023"
    year_match = re.fullmatch(r"\d{4}", date_name.strip())
    if year_match:
        return date(int(date_name.strip()), 1, 1)

    raise ValueError(f"Cannot parse Nomis date: {date_name!r}")


@task(
    name="transform/normalise/to-indicator",
    description="Normalise a source DataFrame to the canonical Indicator schema.",
)
def normalise_to_indicator(
    df: pd.DataFrame,
    indicator_id: str,
    indicator_name: str,
    source: str,
    dataset_code: str,
    reference_period: date,
    lad_col: str,
    lad_name_col: str,
    value_col: str,
    unit: str | None = None,
) -> pd.DataFrame:
    """Map source-specific columns to the canonical ``Indicator`` schema.

    Args:
        df: Input DataFrame from the validate step.
        indicator_id: Machine-readable indicator identifier.
        indicator_name: Human-readable indicator name.
        source: Source system identifier (e.g. ``"nomis"``).
        dataset_code: Dataset / series code within the source.
        reference_period: The date the observations relate to.
        lad_col: Column name for LAD GSS code.
        lad_name_col: Column name for LAD name.
        value_col: Column name for the numeric value.
        unit: Optional unit of measurement.

    Returns:
        DataFrame with columns matching the ``Indicator`` ORM model.
    """
    logger = _get_logger()

    now = datetime.now(UTC)
    lad_codes = df[lad_col].values
    lad_names = df[lad_name_col].values
    result = pd.DataFrame(
        {
            "indicator_id": indicator_id,
            "indicator_name": indicator_name,
            "geography_code": lad_codes,
            "geography_name": lad_names,
            "geography_level": "lad",
            "lad_code": lad_codes,
            "lad_name": lad_names,
            "reference_period": reference_period,
            "value": pd.to_numeric(df[value_col], errors="coerce"),
            "unit": unit,
            "source": source,
            "dataset_code": dataset_code,
            "breakdown_category": "",
            "is_forecast": False,
            "forecast_model": None,
            "created_at": now,
            "updated_at": now,
        }
    )

    result = result.dropna(subset=["value"])
    logger.info("Normalised %d rows for %s", len(result), indicator_id)
    return result


@task(
    name="transform/normalise/nomis-aps",
    description="Normalise a Nomis APS API response to the canonical Indicator schema.",
)
def normalise_nomis_aps(
    df: pd.DataFrame,
    indicator_id: str,
    indicator_name: str,
    dataset_code: str,
    unit: str = "%",
) -> pd.DataFrame:
    """Transform a Nomis APS API response into the Indicator schema.

    Handles the Nomis-specific column names (uppercase) and date format
    (rolling periods like "Jan 2004-Dec 2004").

    Args:
        df: Raw DataFrame from ``extract_aps``.
        indicator_id: Machine-readable indicator identifier.
        indicator_name: Human-readable indicator name.
        dataset_code: Dataset code, e.g. "eejer".
        unit: Unit of measurement (default "%").

    Returns:
        DataFrame with columns matching the ``Indicator`` ORM model.
    """
    logger = _get_logger()

    now = datetime.now(UTC)
    lad_codes = df["GEOGRAPHY_CODE"].values
    lad_names = df["GEOGRAPHY_NAME"].values
    result = pd.DataFrame(
        {
            "indicator_id": indicator_id,
            "indicator_name": indicator_name,
            "geography_code": lad_codes,
            "geography_name": lad_names,
            "geography_level": "lad",
            "lad_code": lad_codes,
            "lad_name": lad_names,
            "reference_period": df["DATE_NAME"].astype(str).apply(_parse_nomis_date),
            "value": pd.to_numeric(df["OBS_VALUE"], errors="coerce"),
            "unit": unit,
            "source": "nomis",
            "dataset_code": dataset_code,
            "breakdown_category": "",
            "is_forecast": False,
            "forecast_model": None,
            "created_at": now,
            "updated_at": now,
        }
    )

    result = result.dropna(subset=["value"])
    logger.info("Normalised %d rows for %s from Nomis APS", len(result), indicator_id)
    return result


@task(
    name="transform/normalise/nomis-ashe",
    description="Normalise a Nomis ASHE API response to the canonical Indicator schema.",
)
def normalise_nomis_ashe(
    df: pd.DataFrame,
    dataset_code: str = "eejpay",
) -> pd.DataFrame:
    """Transform a Nomis ASHE API response into the Indicator schema.

    ASHE returns annual data with DATE_NAME as a plain year string (e.g. "2023").

    Args:
        df: Raw DataFrame from ``extract_ashe``.
        dataset_code: Dataset code (default "eejpay").

    Returns:
        DataFrame with columns matching the ``Indicator`` ORM model.
    """
    logger = _get_logger()

    now = datetime.now(UTC)
    lad_codes = df["GEOGRAPHY_CODE"].values
    lad_names = df["GEOGRAPHY_NAME"].values
    result = pd.DataFrame(
        {
            "indicator_id": "median_weekly_earnings",
            "indicator_name": "Median gross weekly earnings",
            "geography_code": lad_codes,
            "geography_name": lad_names,
            "geography_level": "lad",
            "lad_code": lad_codes,
            "lad_name": lad_names,
            "reference_period": df["DATE_NAME"].astype(str).apply(_parse_nomis_date),
            "value": pd.to_numeric(df["OBS_VALUE"], errors="coerce"),
            "unit": "£",
            "source": "nomis",
            "dataset_code": dataset_code,
            "breakdown_category": "",
            "is_forecast": False,
            "forecast_model": None,
            "created_at": now,
            "updated_at": now,
        }
    )

    result = result.dropna(subset=["value"])
    logger.info("Normalised %d rows for ASHE median weekly earnings", len(result))
    return result


@task(
    name="transform/normalise/nomis-annual",
    description="Normalise any 4-column annual Nomis dataset to the canonical Indicator schema.",
)
def normalise_nomis_annual(
    df: pd.DataFrame,
    indicator_id: str,
    indicator_name: str,
    dataset_code: str,
    unit: str | None = None,
) -> pd.DataFrame:
    """Transform a 4-column annual Nomis response into the Indicator schema.

    Handles Nomis datasets whose API response contains only
    DATE_NAME, GEOGRAPHY_NAME, GEOGRAPHY_CODE, OBS_VALUE — such as
    ASHE (NM_99_1) and Jobs Density (NM_57_1) — where DATE_NAME is a
    plain year string (e.g. "2023").

    Args:
        df: Raw DataFrame from a Nomis extract task.
        indicator_id: Machine-readable indicator identifier.
        indicator_name: Human-readable indicator name.
        dataset_code: Dataset code, e.g. "eejjd".
        unit: Optional unit of measurement.

    Returns:
        DataFrame with columns matching the ``Indicator`` ORM model.
    """
    logger = _get_logger()

    now = datetime.now(UTC)
    lad_codes = df["GEOGRAPHY_CODE"].values
    lad_names = df["GEOGRAPHY_NAME"].values
    result = pd.DataFrame(
        {
            "indicator_id": indicator_id,
            "indicator_name": indicator_name,
            "geography_code": lad_codes,
            "geography_name": lad_names,
            "geography_level": "lad",
            "lad_code": lad_codes,
            "lad_name": lad_names,
            "reference_period": df["DATE_NAME"].astype(str).apply(_parse_nomis_date),
            "value": pd.to_numeric(df["OBS_VALUE"], errors="coerce"),
            "unit": unit,
            "source": "nomis",
            "dataset_code": dataset_code,
            "breakdown_category": "",
            "is_forecast": False,
            "forecast_model": None,
            "created_at": now,
            "updated_at": now,
        }
    )

    result = result.dropna(subset=["value"])
    logger.info("Normalised %d rows for %s", len(result), indicator_id)
    return result


# ---------------------------------------------------------------------------
# Fingertips helpers
# ---------------------------------------------------------------------------


def _resolve_century(start_year: int, end_2digit: int) -> int:
    """Return the full 4-digit end year given a 4-digit start year and a 2-digit end suffix.

    Handles century crossovers correctly: "1999/00" → 2000, "2019/20" → 2020.

    Args:
        start_year: Full 4-digit start year (e.g. 1999 or 2019).
        end_2digit: 2-digit end-year suffix (e.g. 0 for "00", 20 for "20").

    Returns:
        Full 4-digit end year.
    """
    century = start_year // 100
    if end_2digit < start_year % 100:
        century += 1
    return century * 100 + end_2digit


def _parse_fingertips_period(period: str) -> date:
    """Parse a Fingertips time period string to a ``date``.

    Handles three common formats returned by the Fingertips API:

    - Rolling average ``"2018 - 20"`` → ``date(2020, 1, 1)`` (end year)
    - Financial year ``"2019/20"``     → ``date(2020, 1, 1)`` (end year)
    - Single year    ``"2021"``        → ``date(2021, 1, 1)``

    Args:
        period: Raw ``Time period`` string from the Fingertips CSV.

    Returns:
        A ``date`` representing the end of the reported period.

    Raises:
        ValueError: If the string cannot be parsed.
    """
    period = period.strip()

    # "2018 - 20" or "2018-20" — rolling average, take end year
    m = re.fullmatch(r"(\d{4})\s*-\s*(\d{2})", period)
    if m:
        return date(_resolve_century(int(m.group(1)), int(m.group(2))), 1, 1)

    # "2019/20" — financial year, take end year
    m = re.fullmatch(r"(\d{4})/(\d{2})", period)
    if m:
        return date(_resolve_century(int(m.group(1)), int(m.group(2))), 1, 1)

    # "2021" — single calendar year
    if re.fullmatch(r"\d{4}", period):
        return date(int(period), 1, 1)

    raise ValueError(f"Cannot parse Fingertips time period: {period!r}")


@task(
    name="transform/normalise/fingertips",
    description="Normalise a Fingertips API response to the canonical Indicator schema.",
)
def normalise_fingertips(
    df: pd.DataFrame,
    dataset_code: str,
    indicator_id: str,
    indicator_name: str,
    gender_filter: str,
    age_filter: str,
    unit: str | None = None,
) -> pd.DataFrame:
    """Transform a Fingertips API response into the canonical Indicator schema.

    Filters the raw England-wide DataFrame down to Yorkshire LADs and the
    requested sex and age dimensions, then maps columns to the ``Indicator``
    ORM shape.

    Args:
        df: Raw DataFrame from ``extract_fingertips_indicators``.
        dataset_code: Internal dataset code (e.g. ``"sheleb_m"``).
        indicator_id: Machine-readable indicator identifier stored in the DB
            (e.g. ``"life_expectancy_male"``).
        indicator_name: Human-readable indicator name.
        gender_filter: Value of the ``Sex`` column to keep
            (``"Male"``, ``"Female"``, or ``"Persons"``).
        age_filter: Value of the ``Age`` column to keep (e.g. ``"All ages"``
            or ``"10+ yrs"``). Varies by indicator — verify from the API
            before setting.
        unit: Optional unit of measurement (e.g. ``"Years"``).

    Returns:
        DataFrame with columns matching the ``Indicator`` ORM model.
    """
    logger = _get_logger()

    # Filter to the requested sex and age dimensions, and to aggregate rows only.
    # Fingertips includes deprivation breakdowns (populated Category Type) in
    # the same response as the main LAD-level aggregates (null Category Type).
    # We only want the aggregates.
    df = df[
        (df["Sex"] == gender_filter) & (df["Age"] == age_filter) & (df["Category Type"].isna())
    ].copy()

    # Filter to Yorkshire LADs
    df = df[df["Area Code"].isin(YORKSHIRE_LAD_CODES)].copy()

    if df.empty:
        raise ValueError(
            f"No Fingertips data for sex={gender_filter!r} in Yorkshire LADs "
            f"(dataset_code={dataset_code!r}). Check indicator ID and sex filter."
        )

    # Drop rows with no time period, then cast to str before parsing —
    # Fingertips returns mixed-type columns (some years arrive as integers).
    df = df.dropna(subset=["Time period"]).copy()
    df["reference_period"] = df["Time period"].astype(str).apply(_parse_fingertips_period)

    now = datetime.now(UTC)
    lad_codes = df["Area Code"].values
    lad_names = df["Area Name"].values
    result = pd.DataFrame(
        {
            "indicator_id": indicator_id,
            "indicator_name": indicator_name,
            "geography_code": lad_codes,
            "geography_name": lad_names,
            "geography_level": "lad",
            "lad_code": lad_codes,
            "lad_name": lad_names,
            "reference_period": df["reference_period"].values,
            "value": pd.to_numeric(df["Value"], errors="coerce"),
            "unit": unit,
            "source": "fingertips",
            "dataset_code": dataset_code,
            "breakdown_category": "",
            "is_forecast": False,
            "forecast_model": None,
            "created_at": now,
            "updated_at": now,
        }
    )

    result = result.dropna(subset=["value"])
    result = result.drop_duplicates(
        subset=["indicator_id", "lad_code", "reference_period"], keep="last"
    )

    logger.info("Normalised %d Fingertips rows for dataset %s", len(result), dataset_code)
    return result


# ---------------------------------------------------------------------------
# DWP helpers
# ---------------------------------------------------------------------------


def _parse_dwp_period(period_label: str) -> date:
    """Parse a DWP Stat-Xplore period string to a ``date``.

    Handles:
    - Monthly: "July 2024"       → date(2024, 7, 1)
    - Financial year: "2022/23"  → date(2023, 1, 1)  (end year)
    - Plain year: "2022"         → date(2022, 1, 1)

    Raises:
        ValueError: If the string cannot be parsed.
    """
    period_label = period_label.strip()

    # "July 2024" or "Jul 2024"
    m = re.fullmatch(r"([A-Za-z]+)\s+(\d{4})", period_label)
    if m:
        for fmt in ("%d %B %Y", "%d %b %Y"):
            try:
                return datetime.strptime(f"01 {m.group(1)} {m.group(2)}", fmt).date()
            except ValueError:
                continue

    # "Jan-26" — PIP monthly format (abbreviated month, 2-digit year)
    m = re.fullmatch(r"([A-Za-z]{3})-(\d{2})", period_label)
    if m:
        return datetime.strptime(f"01 {m.group(1)} 20{m.group(2)}", "%d %b %Y").date()

    # "2022/23" financial year — resolve to end year
    m = re.fullmatch(r"(\d{4})/(\d{2})", period_label)
    if m:
        return date(_resolve_century(int(m.group(1)), int(m.group(2))), 1, 1)

    # Plain year "2022"
    if re.fullmatch(r"\d{4}", period_label):
        return date(int(period_label), 1, 1)

    raise ValueError(f"Cannot parse DWP period label: {period_label!r}")


@task(
    name="transform/normalise/dwp",
    description="Normalise DWP Stat-Xplore count data to the canonical Indicator schema.",
)
def normalise_dwp(
    df: pd.DataFrame,
    pop_df: pd.DataFrame,
    indicator_id: str,
    indicator_name: str,
    dataset_code: str,
    rate_per: int,
    unit: str,
) -> pd.DataFrame:
    """Transform DWP count data into the Indicator schema as a per-capita rate.

    Joins count data with annual population estimates to compute a rate.
    Population is matched on lad_code and year (derived from reference_period).

    Args:
        df: DataFrame from a DWP extract task with columns:
            period_label, lad_name, lad_code, value (raw count).
        pop_df: Population DataFrame with columns: lad_code, year, population.
            Produced by query_population().
        indicator_id: Machine-readable identifier stored in the DB.
        indicator_name: Human-readable name.
        dataset_code: Dataset code.
        rate_per: Population denominator (e.g. 10_000 or 100_000).
        unit: Unit label (e.g. "per 10k").

    Returns:
        DataFrame with columns matching the ``Indicator`` ORM model.
    """
    logger = _get_logger()

    df = df.copy()
    df["reference_period"] = df["period_label"].apply(_parse_dwp_period)
    df["year"] = df["reference_period"].apply(lambda d: d.year)

    merged = df.merge(
        pop_df[["lad_code", "year", "population"]],
        on=["lad_code", "year"],
        how="left",
    )

    missing_mask = merged["population"].isna()
    if missing_mask.any():
        latest_pop = (
            pop_df.sort_values("year")
            .groupby("lad_code", as_index=False)
            .last()[["lad_code", "population"]]
            .rename(columns={"population": "latest_population"})
        )
        merged = merged.merge(latest_pop, on="lad_code", how="left")
        merged.loc[missing_mask, "population"] = merged.loc[missing_mask, "latest_population"]
        merged = merged.drop(columns=["latest_population"])
        logger.warning(
            "%d rows used most recent available population (no estimate for exact year)",
            missing_mask.sum(),
        )

    merged = merged.dropna(subset=["population", "value"])
    merged = merged[merged["population"] > 0]

    now = datetime.now(UTC)
    result = pd.DataFrame(
        {
            "indicator_id": indicator_id,
            "indicator_name": indicator_name,
            "geography_code": merged["lad_code"],
            "geography_name": merged["lad_name"],
            "geography_level": "lad",
            "lad_code": merged["lad_code"],
            "lad_name": merged["lad_name"],
            "reference_period": merged["reference_period"],
            "value": merged["value"] / merged["population"] * rate_per,
            "unit": unit,
            "source": "dwp",
            "dataset_code": dataset_code,
            "breakdown_category": "",
            "is_forecast": False,
            "forecast_model": None,
            "created_at": now,
            "updated_at": now,
        }
    )

    result = result.dropna(subset=["value"])
    logger.info("Normalised %d rows for %s (rate per %d)", len(result), indicator_id, rate_per)
    return result
