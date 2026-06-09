"""Physical Activity flow.

Extracts physical activity participation data from Sport England's Active Lives
survey for all Yorkshire LADs.
"""

from __future__ import annotations

from datetime import datetime

from prefect import flow
from prefect.artifacts import create_markdown_artifact
from prefect.logging import get_run_logger
from prefect.task_runners import ThreadPoolTaskRunner


@flow(
    name="society-physical-activity",
    flow_run_name=lambda **_: datetime.now().strftime("%B %Y") + " - Society: Physical Activity",
    description="Extract Sport England Active Lives physical activity data for Yorkshire LADs.",
    retries=1,
    retry_delay_seconds=300,
    task_runner=ThreadPoolTaskRunner(max_workers=4),  # type: ignore[arg-type]
)
def physical_activity_flow() -> None:
    """Orchestrate the physical activity ETL pipeline.

    Steps (to be implemented in Phase 2):
        1. Fetch Active Lives data from Sport England API / open data portal.
        2. Filter to Yorkshire LADs.
        3. Normalise to the canonical ``Indicator`` schema.
        4. Upsert into the data warehouse.
        5. Write audit metadata.
    """
    logger = get_run_logger()
    logger.info(
        "No automated extract available: Sport England Active Lives data is a "
        "static biannual release. Reload data manually via load_csv.py when a "
        "new edition is published."
    )
    create_markdown_artifact(
        key="run-summary",
        markdown="Static release - no automated extract. Reload manually via `load_csv.py` when a new edition is published.",
        description="Run summary",
    )
