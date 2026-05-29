"""NOMIS extract tasks.

NOMIS is the ONS labour market statistics API.  It provides access to BRES
(Business Register and Employment Survey) and the Annual Population Survey
(APS), among other datasets.

API docs: https://www.nomisweb.co.uk/api/v01/help
"""

from __future__ import annotations

import logging
from io import StringIO

import pandas as pd
import requests
from prefect import task
from prefect.logging import get_run_logger

from yhovi_pipeline.config import get_settings

_logger = logging.getLogger(__name__)


def _get_logger() -> logging.Logger | logging.LoggerAdapter[logging.Logger]:
    """Return the Prefect run logger if available, else a standard logger."""
    try:
        return get_run_logger()
    except Exception:
        return _logger


BASE_URL = "https://www.nomisweb.co.uk/api/v01/dataset"

# APS percentage dataset (NM_17_5) variable codes for aged 16-64.
APS_VARIABLES: dict[str, int] = {
    "employment_rate": 45,
    "unemployment_rate": 84,
    "self_employment_rate": 74,
    "econ_inactive_rate": 111,
    "qualifications_rqf4plus": 1902,
    "no_qualifications": 1947,
}

# Columns to request from the APS API.
_APS_SELECT = "date_name,geography_name,geography_code,variable_name,variable_code,obs_value"

# Columns to request from the ASHE API.
_ASHE_SELECT = "date_name,geography_name,geography_code,obs_value"


def _build_nomis_url(
    dataset: str,
    *,
    geography: list[str],
    time: str = "latest",
    select: str | None = None,
    uid: str | None = None,
    **extra_params: object,
) -> str:
    """Build a Nomis API CSV request URL.

    Args:
        dataset: Nomis dataset ID, e.g. "NM_17_5" or "NM_99_1".
        geography: List of ONS GSS codes.
        time: Time parameter, e.g. "latest" or "2023-12".
        select: Comma-separated column names to return.
        uid: Optional Nomis API key (uid) for higher rate limits.
        **extra_params: Dataset-specific parameters (e.g. variable, pay, sex, item,
            measures). List values are joined with commas.
    """

    def _fmt(v: object) -> str:
        return ",".join(str(x) for x in v) if isinstance(v, list) else str(v)

    params = {"geography": ",".join(geography), "time": time}
    params.update({k: _fmt(v) for k, v in extra_params.items()})
    if select:
        params["select"] = select
    if uid:
        params["uid"] = uid

    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{BASE_URL}/{dataset}.data.csv?{query}"


def _fetch_nomis_csv(url: str) -> pd.DataFrame:
    """Fetch a CSV from the Nomis API and return as a DataFrame."""
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text))


@task(
    name="extract/nomis/aps",
    description="Extract Annual Population Survey data from NOMIS for Yorkshire LADs.",
    retries=3,
    retry_delay_seconds=60,
)
def extract_aps(
    variable: str,
    time: str = "latest",
) -> pd.DataFrame:
    """Fetch Annual Population Survey percentage data from NOMIS.

    Args:
        variable: Key into APS_VARIABLES, e.g. "employment_rate".
        time: Time parameter — "latest", a specific period like "2023-12",
            or a range like "2004-12-2024-12".

    Returns:
        DataFrame with columns: date_name, geography_name, geography_code,
        variable_name, variable_code, obs_value.
    """
    logger = _get_logger()
    settings = get_settings()

    if variable not in APS_VARIABLES:
        raise ValueError(
            f"Unknown APS variable {variable!r}. Valid keys: {list(APS_VARIABLES.keys())}"
        )

    lad_codes = settings.yorkshire_lad_codes
    uid = settings.nomis_api_key.get_secret_value() if settings.nomis_api_key else None

    url = _build_nomis_url(
        "NM_17_5",
        geography=lad_codes,
        variable=[APS_VARIABLES[variable]],
        measures=20599,
        time=time,
        select=_APS_SELECT,
        uid=uid,
    )

    logger.info(
        "Fetching APS %s from Nomis: %s",
        variable,
        url if not uid else url.split("uid=")[0] + "uid=***",
    )
    df = _fetch_nomis_csv(url)
    logger.info("Received %d rows for APS %s", len(df), variable)

    return df


@task(
    name="extract/nomis/ashe",
    description="Extract ASHE gross weekly earnings from NOMIS for Yorkshire LADs.",
    retries=3,
    retry_delay_seconds=60,
)
def extract_ashe(time: str = "latest") -> pd.DataFrame:
    """Fetch Annual Survey of Hours and Earnings (ASHE) data from NOMIS.

    Returns median gross weekly pay, workplace-based, for all workers
    (total: all genders, full and part time combined).

    Args:
        time: Time parameter — "latest" for most recent year, or a range
            like "2010,2011,2012,...,2024" for historical data.

    Returns:
        DataFrame with columns: date_name, geography_name, geography_code,
        obs_value.
    """
    logger = _get_logger()
    settings = get_settings()

    lad_codes = settings.yorkshire_lad_codes
    uid = settings.nomis_api_key.get_secret_value() if settings.nomis_api_key else None

    url = _build_nomis_url(
        "NM_99_1",
        geography=lad_codes,
        pay=1,  # Gross weekly pay
        sex=7,  # Total (all genders + employment types)
        item=2,  # Median
        measures=20100,  # Value
        time=time,
        select=_ASHE_SELECT,
        uid=uid,
    )

    logger.info("Fetching ASHE weekly earnings from Nomis")
    df = _fetch_nomis_csv(url)
    logger.info("Received %d rows from ASHE", len(df))
    return df


@task(
    name="extract/nomis/jobs-density",
    description="Extract ONS Jobs Density from NOMIS NM_57_1 for Yorkshire LADs.",
    retries=3,
    retry_delay_seconds=60,
)
def extract_jobs_density(time: str = "latest") -> pd.DataFrame:
    """Fetch ONS Jobs Density data from NOMIS (NM_57_1).

    Jobs density is defined as total filled jobs divided by the resident
    working-age population (16-64) in that area.  Item 3 selects the
    pre-calculated ratio; item 1 would return the raw jobs count.

    Args:
        time: Time parameter — "latest" for most recent year, or a range
            like "2010,2011,...,2023" for historical data.

    Returns:
        DataFrame with columns: date_name, geography_name, geography_code,
        obs_value.
    """
    logger = _get_logger()
    settings = get_settings()

    lad_codes = settings.yorkshire_lad_codes
    uid = settings.nomis_api_key.get_secret_value() if settings.nomis_api_key else None

    url = _build_nomis_url(
        "NM_57_1",
        geography=lad_codes,
        item=3,  # Jobs density ratio; item=1 would be raw jobs count
        time=time,
        select=_ASHE_SELECT,
        uid=uid,
    )

    logger.info("Fetching Jobs Density from Nomis")
    df = _fetch_nomis_csv(url)
    logger.info("Received %d rows from Jobs Density", len(df))
    return df
