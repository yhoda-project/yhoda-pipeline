"""NHS Fingertips extract tasks.

NHS Fingertips (fingertips.phe.org.uk) provides the Public Health Profiles API
with hundreds of public health indicators at LAD and sub-LAD geographies.

API docs: https://fingertips.phe.org.uk/api

Data is fetched as CSV for all England LADs (area_type_id=402, parent=England).
Yorkshire LAD filtering happens in the normalise step.
"""

from __future__ import annotations

import logging
from io import StringIO

import pandas as pd
import requests
from prefect import task
from prefect.logging import get_run_logger

_logger = logging.getLogger(__name__)

BASE_URL = "https://fingertips.phe.org.uk/api"

# Fingertips area type ID for Local Authority Districts (2019 boundaries).
LAD_AREA_TYPE_ID = 402

# ONS GSS code for England — used as the parent area when fetching all LADs.
ENGLAND_PARENT_CODE = "E92000001"

# Minimum columns the Fingertips CSV must contain for downstream tasks.
FINGERTIPS_REQUIRED_COLUMNS = [
    "Indicator ID",
    "Indicator Name",
    "Area Code",
    "Area Name",
    "Sex",
    "Time period",
    "Value",
]


def _get_logger() -> logging.Logger | logging.LoggerAdapter[logging.Logger]:
    try:
        return get_run_logger()
    except Exception:
        return _logger


@task(
    name="extract/fingertips/indicators",
    description="Extract health outcome indicators from NHS Fingertips for all England LADs.",
    retries=3,
    retry_delay_seconds=60,
)
def extract_fingertips_indicators(indicator_id: int) -> pd.DataFrame:
    """Fetch all available data for a single Fingertips indicator across England LADs.

    Data is returned for all time periods available in Fingertips (i.e. the full
    historical series), not just the latest year.  Yorkshire LAD filtering is
    applied in the normalise step so that the raw DataFrame can be inspected in
    full if needed.

    Args:
        indicator_id: Fingertips numeric indicator ID.  Examples:
            41001 = Under-75 preventable mortality,
            90366 = Life expectancy at birth,
            90048 = Healthy life expectancy at birth.

    Returns:
        DataFrame with the raw Fingertips CSV columns, including at minimum:
        ``Indicator ID``, ``Indicator Name``, ``Area Code``, ``Area Name``,
        ``Sex``, ``Time period``, ``Value``.
    """
    logger = _get_logger()

    url = (
        f"{BASE_URL}/all_data/csv/by_indicator_id"
        f"?indicator_ids={indicator_id}"
        f"&area_type_id={LAD_AREA_TYPE_ID}"
        f"&parent_area_code={ENGLAND_PARENT_CODE}"
    )

    logger.info("Fetching Fingertips indicator %d", indicator_id)
    response = requests.get(url, timeout=120)
    response.raise_for_status()

    df = pd.read_csv(StringIO(response.text), low_memory=False)
    logger.info("Received %d rows for Fingertips indicator %d", len(df), indicator_id)
    return df
