"""Sport England Active Lives extract tasks.

Sport England publishes Active Lives survey data showing physical activity
participation rates at LAD level.
"""

from __future__ import annotations

import pandas as pd
from prefect import task


@task(
    name="extract/sport-england/active-lives",
    description="Extract Sport England Active Lives data for Yorkshire LADs.",
    retries=3,
    retry_delay_seconds=60,
)
def extract_active_lives(survey_year: str) -> pd.DataFrame:
    """Fetch Active Lives participation data from Sport England.

    Args:
        survey_year: Survey year string, e.g. ``"2023-24"``.

    Returns:
        DataFrame with physical activity rates for Yorkshire LADs.
    """
    raise NotImplementedError(
        "No automated extract available. Sport England Active Lives data is only "
        "accessible through an interactive portal with no download API. Load manually "
        "via load_csv.py."
    )
