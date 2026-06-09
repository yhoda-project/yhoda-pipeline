"""Claimant Count flow.

Extracts Children in Low Income and PIP claimant count data from DWP
Stat-Xplore for all Yorkshire LADs and loads them into the data warehouse
as per-capita rates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from prefect import flow
from prefect.artifacts import create_table_artifact
from prefect.task_runners import ThreadPoolTaskRunner

from yhovi_pipeline.db.models import ExtractionStatus
from yhovi_pipeline.tasks.extract.dwp import extract_children_low_income, extract_pip_claimants
from yhovi_pipeline.tasks.load.database import query_population, upsert_indicators, write_metadata
from yhovi_pipeline.tasks.transform.normalise import normalise_dwp
from yhovi_pipeline.utils.notify import send_failure_alert


@dataclass
class _DatasetConfig:
    extract_fn: Any  # Prefect Task - Any avoids callable-overload complications
    dataset_code: str
    indicator_id: str
    indicator_name: str
    rate_per: int
    unit: str


_DATASETS = [
    _DatasetConfig(
        extract_fn=extract_children_low_income,
        dataset_code="eeicli",
        indicator_id="children_low_income_per_10k",
        indicator_name="Number of children in relative low income households per 10,000 inhabitants",
        rate_per=10_000,
        unit="per 10k",
    ),
    _DatasetConfig(
        extract_fn=extract_pip_claimants,
        dataset_code="eejpip",
        indicator_id="disability_benefits_per_100k",
        indicator_name="Number of People with Disability Benefits per 100,000 Residents",
        rate_per=100_000,
        unit="per 100k",
    ),
]


@flow(
    name="economy-claimant-count",
    flow_run_name=lambda **_: datetime.now().strftime("%B %Y") + " - Economy: Claimant Count",
    description="Extract DWP claimant count data for Yorkshire LADs.",
    retries=1,
    retry_delay_seconds=300,
    task_runner=ThreadPoolTaskRunner(max_workers=4),  # type: ignore[arg-type]
)
def claimant_count_flow() -> None:
    """Orchestrate the DWP claimant count ETL pipeline.

    Extracts Children in Low Income and PIP claimant counts from DWP
    Stat-Xplore, normalises to per-capita rates using population already
    in the indicator table, and upserts into the data warehouse.
    """
    pop_df = query_population()

    failures: list[str] = []
    results: list[dict[str, Any]] = []

    for ds in _DATASETS:
        try:
            raw_df = ds.extract_fn()

            indicator_df = normalise_dwp(
                df=raw_df,
                pop_df=pop_df,
                indicator_id=ds.indicator_id,
                indicator_name=ds.indicator_name,
                dataset_code=ds.dataset_code,
                rate_per=ds.rate_per,
                unit=ds.unit,
            )

            rows_loaded = upsert_indicators(df=indicator_df, dataset_code=ds.dataset_code)

            write_metadata(
                dataset_code=ds.dataset_code,
                source="dwp",
                status=ExtractionStatus.SUCCESS,
                rows_extracted=len(raw_df),
                rows_loaded=rows_loaded,
            )

            results.append(
                {
                    "Dataset": ds.dataset_code,
                    "Rows extracted": len(raw_df),
                    "Rows loaded": rows_loaded,
                    "Status": "OK",
                }
            )

        except Exception as e:
            write_metadata(
                dataset_code=ds.dataset_code,
                source="dwp",
                status=ExtractionStatus.FAILED,
                error_message=str(e)[:500],
            )
            results.append(
                {
                    "Dataset": ds.dataset_code,
                    "Rows extracted": "-",
                    "Rows loaded": "-",
                    "Status": "Failed",
                }
            )
            failures.append(f"{ds.dataset_code}: {e}")

    if results:
        create_table_artifact(key="load-summary", table=results, description="Load summary")

    if failures:
        error = f"DWP claimant count failed for: {'; '.join(failures)}"
        send_failure_alert("economy-claimant-count", error)
        raise RuntimeError(error)
