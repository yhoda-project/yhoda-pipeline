"""Crime Statistics flow.

Extracts recorded crime data from the Home Office / ONS for all Yorkshire LADs.
"""

from __future__ import annotations

from datetime import datetime

from prefect import flow
from prefect.artifacts import create_markdown_artifact
from prefect.logging import get_run_logger
from prefect.task_runners import ThreadPoolTaskRunner


@flow(
    name="society-crime-statistics",
    flow_run_name=lambda **_: datetime.now().strftime("%B %Y") + " — Society: Crime Statistics",
    description="Extract Home Office recorded crime statistics for Yorkshire LADs.",
    retries=1,
    retry_delay_seconds=300,
    task_runner=ThreadPoolTaskRunner(max_workers=4),  # type: ignore[arg-type]
)
def crime_statistics_flow() -> None:
    """Orchestrate the crime statistics ETL pipeline.

    Steps (to be implemented in Phase 2):
        1. Download ONS / Home Office crime tables for Yorkshire.
        2. Parse and validate the data.
        3. Normalise to the canonical ``Indicator`` schema.
        4. Upsert into the data warehouse.
        5. Write audit metadata.
    """
    logger = get_run_logger()
    logger.info(
        "No automated extract available: Home Office / ONS crime statistics "
        "are static annual releases. Reload data manually via load_csv.py "
        "when a new edition is published."
    )
    create_markdown_artifact(
        key="run-summary",
        markdown="Static release — no automated extract. Reload manually via `load_csv.py` when a new edition is published.",
        description="Run summary",
    )
