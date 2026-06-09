"""DESNZ greenhouse gas emissions extract tasks.

DESNZ publishes UK local authority and regional greenhouse gas emissions
estimates annually. There is no stable download API; data is loaded manually
via load_csv.py.
"""

from __future__ import annotations

import pandas as pd
from prefect import task


@task(
    name="extract/desnz/ghg-emissions",
    description="Extract DESNZ greenhouse gas emissions data for Yorkshire LADs.",
    retries=3,
    retry_delay_seconds=60,
)
def extract_ghg_emissions(reference_year: int) -> pd.DataFrame:
    """Fetch DESNZ UK local authority greenhouse gas emissions estimates.

    DESNZ does not provide a machine-readable API for this dataset.
    Data is loaded manually via load_csv.py when a new edition is published.

    Args:
        reference_year: The calendar year to extract.

    Returns:
        DataFrame with CO2, CH4, and N2O emissions per capita for Yorkshire LADs.
    """
    raise NotImplementedError(
        "No automated extract available. Load emissions data manually via load_csv.py."
    )
