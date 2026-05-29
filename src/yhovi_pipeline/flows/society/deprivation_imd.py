"""Deprivation / IMD flow.

Extracts Indices of Multiple Deprivation (IMD) scores and ranks from MHCLG
for all Yorkshire LADs.
"""

from __future__ import annotations

from datetime import datetime

from prefect import flow
from prefect.artifacts import create_markdown_artifact
from prefect.logging import get_run_logger
from prefect.task_runners import ThreadPoolTaskRunner


@flow(
    name="society-deprivation-imd",
    flow_run_name=lambda **_: datetime.now().strftime("%B %Y") + " — Society: Deprivation (IMD)",
    description="Extract MHCLG Indices of Multiple Deprivation for Yorkshire LADs.",
    retries=1,
    retry_delay_seconds=300,
    task_runner=ThreadPoolTaskRunner(max_workers=4),  # type: ignore[arg-type]
)
def deprivation_imd_flow() -> None:
    """Orchestrate the IMD ETL pipeline.

    Steps (to be implemented in Phase 2):
        1. Download MHCLG IMD release for Yorkshire LADs.
        2. Parse the LSOA-level scores.
        3. Aggregate to LAD using the geo lookup.
        4. Normalise to the canonical ``Indicator`` schema.
        5. Upsert into the data warehouse.
        6. Write audit metadata.
    """
    logger = get_run_logger()
    logger.info(
        "No automated extract available: MHCLG Indices of Multiple Deprivation "
        "is published every ~4 years as a static release. Reload data manually "
        "via load_csv.py when a new edition is published."
    )
    create_markdown_artifact(
        key="run-summary",
        markdown="Static release — no automated extract. Reload manually via `load_csv.py` when a new edition is published.",
        description="Run summary",
    )
