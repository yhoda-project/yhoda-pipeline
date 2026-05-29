"""Data validation transform tasks.

Validates raw extracted DataFrames against expected schemas and business rules
before passing them to the normalise step.
"""

from __future__ import annotations

import logging

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


@task(
    name="transform/validate/schema",
    description="Validate a raw extracted DataFrame against the expected schema.",
)
def validate_schema(
    df: pd.DataFrame,
    required_columns: list[str],
    source: str,
) -> pd.DataFrame:
    """Check that a DataFrame has the required columns and non-zero rows.

    Args:
        df: The raw extracted DataFrame to validate.
        required_columns: List of column names that must be present.
        source: Source system name (used in error messages).

    Returns:
        The validated DataFrame (unchanged if validation passes).

    Raises:
        ValueError: If required columns are missing or the DataFrame is empty.
    """
    logger = _get_logger()

    if df.empty:
        raise ValueError(f"Empty DataFrame received from {source}")

    missing = set(required_columns) - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing columns from {source}: {sorted(missing)}. Got: {list(df.columns)}"
        )

    logger.info("Schema OK for %s: %d rows, columns %s", source, len(df), list(df.columns))
    return df


@task(
    name="transform/validate/yorkshire-lads",
    description="Check that all expected Yorkshire LAD codes are present in the data.",
)
def validate_yorkshire_lads(df: pd.DataFrame, lad_col: str = "lad_code") -> pd.DataFrame:
    """Warn (but do not fail) if any expected Yorkshire LAD codes are absent.

    Args:
        df: DataFrame containing a LAD code column.
        lad_col: Name of the LAD code column.

    Returns:
        The input DataFrame unchanged.
    """
    logger = _get_logger()

    present = set(df[lad_col].unique())
    expected = set(YORKSHIRE_LAD_CODES)
    missing = expected - present

    if missing:
        logger.warning("Missing %d Yorkshire LAD codes: %s", len(missing), sorted(missing))
    else:
        logger.info("All %d Yorkshire LAD codes present", len(expected))

    return df
