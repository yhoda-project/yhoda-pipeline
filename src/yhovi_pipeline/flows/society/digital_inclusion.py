"""Digital Inclusion flow.

Extracts broadband availability, speed, and digital skills indicators from
Ofcom Connected Nations and DCMS data for all Yorkshire LADs.
"""

from __future__ import annotations

from datetime import datetime

from prefect import flow
from prefect.artifacts import create_markdown_artifact
from prefect.logging import get_run_logger
from prefect.task_runners import ThreadPoolTaskRunner


@flow(
    name="society-digital-inclusion",
    flow_run_name=lambda **_: datetime.now().strftime("%B %Y") + " — Society: Digital Inclusion",
    description="Extract Ofcom / DCMS digital inclusion indicators for Yorkshire LADs.",
    retries=1,
    retry_delay_seconds=300,
    task_runner=ThreadPoolTaskRunner(max_workers=4),  # type: ignore[arg-type]
)
def digital_inclusion_flow() -> None:
    """Orchestrate the digital inclusion ETL pipeline.

    Steps (to be implemented in Phase 2):
        1. Download Ofcom Connected Nations datasets for Yorkshire.
        2. Parse broadband coverage and speed statistics.
        3. Normalise to the canonical ``Indicator`` schema.
        4. Upsert into the data warehouse.
        5. Write audit metadata.
    """
    logger = get_run_logger()
    logger.info(
        "No automated extract available: Ofcom Connected Nations data is a "
        "static annual release. Reload data manually via load_csv.py when a "
        "new edition is published."
    )
    create_markdown_artifact(
        key="run-summary",
        markdown="Static release — no automated extract. Reload manually via `load_csv.py` when a new edition is published.",
        description="Run summary",
    )
