"""GDP / GVA flow.

Extracts Gross Value Added (balanced) and regional GDP estimates from the ONS
Regional Accounts publication for Yorkshire LADs.
"""

from __future__ import annotations

from datetime import datetime

from prefect import flow
from prefect.artifacts import create_markdown_artifact
from prefect.logging import get_run_logger
from prefect.task_runners import ThreadPoolTaskRunner


@flow(
    name="economy-gdp-gva",
    flow_run_name=lambda **_: datetime.now().strftime("%B %Y") + " - Economy: GDP / GVA",
    description="Extract ONS GVA / regional GDP data for Yorkshire LADs.",
    retries=1,
    retry_delay_seconds=300,
    task_runner=ThreadPoolTaskRunner(max_workers=4),  # type: ignore[arg-type]
)
def gdp_gva_flow() -> None:
    """Orchestrate the GVA / GDP ETL pipeline.

    Steps (to be implemented in Phase 2):
        1. Download ONS Regional Accounts tables for Yorkshire.
        2. Parse XLSX / CSV release.
        3. Normalise to the canonical ``Indicator`` schema.
        4. Upsert into the data warehouse.
        5. Write audit metadata.
    """
    logger = get_run_logger()
    logger.info(
        "No automated extract available: ONS Regional Accounts (GVA/GDP) is a "
        "static annual release. Reload data manually via load_csv.py when a "
        "new edition is published."
    )
    create_markdown_artifact(
        key="run-summary",
        markdown="Static release - no automated extract. Reload manually via `load_csv.py` when a new edition is published.",
        description="Run summary",
    )
