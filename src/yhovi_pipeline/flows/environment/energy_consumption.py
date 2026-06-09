"""Energy Consumption flow.

Extracts sub-national electricity and gas consumption data from BEIS / DESNZ
for all Yorkshire LADs.
"""

from __future__ import annotations

from datetime import datetime

from prefect import flow
from prefect.artifacts import create_markdown_artifact
from prefect.logging import get_run_logger
from prefect.task_runners import ThreadPoolTaskRunner


@flow(
    name="environment-energy-consumption",
    flow_run_name=lambda **_: (
        datetime.now().strftime("%B %Y") + " - Environment: Energy Consumption"
    ),
    description="Extract BEIS sub-national energy consumption data for Yorkshire LADs.",
    retries=1,
    retry_delay_seconds=300,
    task_runner=ThreadPoolTaskRunner(max_workers=4),  # type: ignore[arg-type]
)
def energy_consumption_flow() -> None:
    """Orchestrate the energy consumption ETL pipeline.

    Steps (to be implemented in Phase 2):
        1. Download BEIS Sub-national Electricity / Gas Consumption Statistics.
        2. Filter to Yorkshire LADs.
        3. Normalise to the canonical ``Indicator`` schema.
        4. Upsert into the data warehouse.
        5. Write audit metadata.
    """
    logger = get_run_logger()
    logger.info(
        "No automated extract available: BEIS sub-national energy consumption "
        "data is a static annual release. Reload data manually via load_csv.py "
        "when a new edition is published."
    )
    create_markdown_artifact(
        key="run-summary",
        markdown="Static release - no automated extract. Reload manually via `load_csv.py` when a new edition is published.",
        description="Run summary",
    )
