"""Ofcom Connected Nations extract tasks.

Ofcom publishes Connected Nations reports with broadband availability and
speed statistics at LAD level.
"""

from __future__ import annotations

import pandas as pd
from prefect import task


@task(
    name="extract/ofcom/connected-nations",
    description="Extract Ofcom Connected Nations broadband data for Yorkshire LADs.",
    retries=3,
    retry_delay_seconds=60,
)
def extract_connected_nations(reference_year: int) -> pd.DataFrame:
    """Fetch Ofcom Connected Nations broadband statistics.

    Args:
        reference_year: The publication year to extract.

    Returns:
        DataFrame with broadband coverage and speed data for Yorkshire LADs.
    """
    raise NotImplementedError(
        "No automated extract available. Ofcom Connected Nations data is published as "
        "an annual ZIP with a URL that changes each year. Load manually via load_csv.py."
    )
