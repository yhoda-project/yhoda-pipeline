"""DWP Stat-Xplore extract tasks.

DWP Stat-Xplore provides access to benefit claimant statistics including
Personal Independence Payment (PIP) and Children in Low Income Families data.

API docs: https://stat-xplore.dwp.gov.uk/webapi/online-help/Open-Data-API.html
"""

from __future__ import annotations

import itertools
import logging
from typing import Any

import pandas as pd
import requests
from prefect import task
from prefect.logging import get_run_logger

from yhovi_pipeline.config import YORKSHIRE_LAD_CODES, get_settings

_logger = logging.getLogger(__name__)

_BASE = "https://stat-xplore.dwp.gov.uk/webapi/rest/v1"


def _get_logger() -> logging.Logger | logging.LoggerAdapter[logging.Logger]:
    try:
        return get_run_logger()
    except Exception:
        return _logger


# ---------------------------------------------------------------------------
# Dataset and field identifiers
# ---------------------------------------------------------------------------
# IDs sourced from GET /schema → GET /schema/{database_id} → GET group href.
# Geography fields are FIELD type children inside a GROUP; results are
# filtered to Yorkshire LADs post-fetch. To re-verify or discover new IDs,
# call browse_stat_xplore_schema().

_CIL_DATABASE = "str:database:CILIF_AHC"
_CIL_MEASURE = "str:count:CILIF_AHC:V_F_CILIF_AHC"
_CIL_LA_FIELD = "str:field:CILIF_AHC:V_F_CILIF_AHC:UK_COA_CODE"
_CIL_LA_VALUESET = "V_C_MASTERGEOG21_LA_TO_REGION_NI"
_CIL_DATE_FIELD = "str:field:CILIF_AHC:F_CILIF_DATE_AHC:DATE_NAME"

_PIP_DATABASE = "str:database:PIP_Monthly_new"
_PIP_MEASURE = "str:count:PIP_Monthly_new:V_F_PIP_MONTHLY"
_PIP_LA_FIELD = "str:field:PIP_Monthly_new:V_F_PIP_MONTHLY:COA_CODE"
_PIP_LA_VALUESET = "V_C_MASTERGEOG21_LA_TO_REGION"
_PIP_DATE_FIELD = "str:field:PIP_Monthly_new:F_PIP_DATE:DATE2"


def _headers(api_key: str) -> dict[str, str]:
    return {"APIKey": api_key, "Content-Type": "application/json"}


def _post_table(payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    """POST a table query to Stat-Xplore and return the JSON response.

    Raises:
        PermissionError: On HTTP 401 (invalid API key).
        RuntimeError: On HTTP 429 (rate limit exceeded).
        requests.HTTPError: On any other non-2xx response.
    """
    resp = requests.post(
        f"{_BASE}/table",
        json=payload,
        headers=_headers(api_key),
        timeout=120,
    )
    if resp.status_code == 401:
        raise PermissionError("DWP Stat-Xplore: invalid or missing API key (HTTP 401)")
    if resp.status_code == 429:
        raise RuntimeError("DWP Stat-Xplore: rate limit exceeded — retry later (HTTP 429)")
    resp.raise_for_status()
    return resp.json()  # type: ignore[no-any-return]


def _gss_from_uri(uri: str) -> str:
    """Extract an ONS GSS code from a Stat-Xplore geography URI.

    Stat-Xplore geography URIs embed the GSS code as the final segment:
        str:val:<db>:<field>:E08000032  →  E08000032
    """
    return uri.split(":")[-1]


def _flatten_cube(response: dict[str, Any]) -> pd.DataFrame:
    """Flatten a Stat-Xplore /table response into a long-format DataFrame.

    The response contains a multi-dimensional cube where values are indexed
    by dimension position.  This iterates over all index combinations and
    emits one row per combination with the field labels and value.

    Returns:
        DataFrame with one column per field label, a URI column per field,
        and a 'value' column.
    """
    fields = response["fields"]
    cube_values = next(iter(response["cubes"].values()))["values"]

    rows = []
    counts = [len(f["items"]) for f in fields]
    for indices in itertools.product(*[range(n) for n in counts]):
        val: Any = cube_values
        for idx in indices:
            val = val[idx]

        row: dict[str, Any] = {"value": val}
        for dim, field in enumerate(fields):
            item = field["items"][indices[dim]]
            row[field["label"]] = item["labels"][0]
            row[f"{field['label']}_uri"] = item["uris"][0]
        rows.append(row)

    return pd.DataFrame(rows)


def browse_stat_xplore_schema(api_key: str) -> dict[str, Any]:
    """Return the top-level Stat-Xplore schema listing all available databases.

    Use this to discover or re-verify database and field IDs.

    Example::

        from yhovi_pipeline.tasks.extract.dwp import browse_stat_xplore_schema
        from yhovi_pipeline.config import get_settings
        import pprint
        schema = browse_stat_xplore_schema(get_settings().dwp_api_key.get_secret_value())
        for db in schema["children"]:
            print(db["id"], db["label"])
    """
    resp = requests.get(
        f"{_BASE}/schema",
        headers=_headers(api_key),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()  # type: ignore[no-any-return]


def _extract_dwp_table(
    database: str,
    measure: str,
    la_field: str,
    la_valueset: str,
    date_field: str,
    dataset_label: str,
    api_key: str,
) -> pd.DataFrame:
    """Generic Stat-Xplore extractor for a date x local-authority table.

    Uses recodes to request only Yorkshire LAD items, flattens the cube
    response, and extracts GSS codes from geography URIs.

    Returns:
        DataFrame with columns: period_label, lad_name, lad_code, value.
    """
    logger = _get_logger()

    db_id = database.split(":")[-1]
    field_path = ":".join(la_field.split(":")[3:])
    la_item_prefix = f"str:value:{db_id}:{field_path}:{la_valueset}"

    payload: dict[str, Any] = {
        "database": database,
        "measures": [measure],
        "dimensions": [
            [date_field],
            [la_field],
        ],
        "recodes": {
            la_field: {
                "map": [[f"{la_item_prefix}:{code}"] for code in YORKSHIRE_LAD_CODES],
                "total": False,
            }
        },
    }

    logger.info("Fetching %s from DWP Stat-Xplore", dataset_label)
    response = _post_table(payload, api_key)
    df = _flatten_cube(response)
    logger.info("Received %d rows before filtering", len(df))

    date_label = response["fields"][0]["label"]
    la_label = response["fields"][1]["label"]

    df["lad_code"] = df[f"{la_label}_uri"].apply(_gss_from_uri)
    df = df[df["lad_code"].isin(YORKSHIRE_LAD_CODES)].copy()
    df = df.rename(columns={date_label: "period_label", la_label: "lad_name"})
    df = df[["period_label", "lad_name", "lad_code", "value"]].dropna(subset=["value"])

    logger.info("Returning %d rows for Yorkshire LADs (%s)", len(df), dataset_label)
    return df


@task(
    name="extract/dwp/children-low-income",
    description="Extract Children in Low Income Families count from DWP Stat-Xplore.",
    retries=3,
    retry_delay_seconds=60,
)
def extract_children_low_income() -> pd.DataFrame:
    """Fetch Children in Low Income Families (local area statistics) from Stat-Xplore.

    Returns all available periods for Yorkshire LADs.

    Returns:
        DataFrame with columns: period_label, lad_name, lad_code, value (count).
    """
    settings = get_settings()
    return _extract_dwp_table(
        database=_CIL_DATABASE,
        measure=_CIL_MEASURE,
        la_field=_CIL_LA_FIELD,
        la_valueset=_CIL_LA_VALUESET,
        date_field=_CIL_DATE_FIELD,
        dataset_label="Children in Low Income",
        api_key=settings.dwp_api_key.get_secret_value(),
    )


@task(
    name="extract/dwp/pip-claimants",
    description="Extract PIP claimant count from DWP Stat-Xplore.",
    retries=3,
    retry_delay_seconds=60,
)
def extract_pip_claimants() -> pd.DataFrame:
    """Fetch Personal Independence Payment (PIP) claimant counts from Stat-Xplore.

    Returns all available periods for Yorkshire LADs.

    Returns:
        DataFrame with columns: period_label, lad_name, lad_code, value (count).
    """
    settings = get_settings()
    return _extract_dwp_table(
        database=_PIP_DATABASE,
        measure=_PIP_MEASURE,
        la_field=_PIP_LA_FIELD,
        la_valueset=_PIP_LA_VALUESET,
        date_field=_PIP_DATE_FIELD,
        dataset_label="PIP claimants",
        api_key=settings.dwp_api_key.get_secret_value(),
    )
