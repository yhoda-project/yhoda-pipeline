"""Education Attainment flow.

Extracts qualification level data from NOMIS (APS dataset NM_17_5)
for all Yorkshire LADs and loads them into the data warehouse.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from prefect import flow
from prefect.artifacts import create_table_artifact
from prefect.task_runners import ThreadPoolTaskRunner

from yhovi_pipeline.db.models import ExtractionStatus
from yhovi_pipeline.tasks.extract.nomis import extract_aps
from yhovi_pipeline.tasks.load.database import upsert_indicators, write_metadata
from yhovi_pipeline.tasks.transform.normalise import normalise_nomis_aps
from yhovi_pipeline.tasks.transform.validate import validate_schema
from yhovi_pipeline.utils.notify import send_failure_alert

# APS qualification variables mapped to indicator metadata.
QUALIFICATION_DATASETS: dict[str, dict[str, str]] = {
    "qualifications_rqf4plus": {
        "indicator_id": "qualifications_rqf4plus",
        "indicator_name": "% aged 16-64 qualified to RQF level 4 and above",
        "dataset_code": "eeeql4",
        "unit": "%",
    },
    "no_qualifications": {
        "indicator_id": "no_qualifications",
        "indicator_name": "% aged 16-64 with no qualifications",
        "dataset_code": "eeeqnone",
        "unit": "%",
    },
}

NOMIS_APS_COLUMNS = [
    "DATE_NAME",
    "GEOGRAPHY_NAME",
    "GEOGRAPHY_CODE",
    "VARIABLE_NAME",
    "VARIABLE_CODE",
    "OBS_VALUE",
]


@flow(
    name="society-education-attainment",
    flow_run_name=lambda **_: datetime.now().strftime("%B %Y") + " — Society: Education Attainment",
    description="Extract qualification attainment data from NOMIS APS for Yorkshire LADs.",
    retries=1,
    retry_delay_seconds=300,
    task_runner=ThreadPoolTaskRunner(max_workers=4),  # type: ignore[arg-type]
)
def education_attainment_flow(time: str = "latestMinus1,latest") -> None:
    """Orchestrate the education attainment ETL pipeline.

    Extracts APS qualification indicators from NOMIS, validates,
    normalises to the Indicator schema, and upserts into the PostgreSQL
    data warehouse.

    Args:
        time: Nomis time parameter. Defaults to the two most recent periods
            so that if the latest APS period has not yet been published for
            qualification variables, the previous period is still loaded.
    """
    results: list[dict[str, Any]] = []
    try:
        for variable_key, meta in QUALIFICATION_DATASETS.items():
            dataset_code = meta["dataset_code"]

            try:
                raw_df = extract_aps(variable=variable_key, time=time)

                validated_df = validate_schema(
                    df=raw_df,
                    required_columns=NOMIS_APS_COLUMNS,
                    source="nomis",
                )

                indicator_df = normalise_nomis_aps(
                    df=validated_df,
                    indicator_id=meta["indicator_id"],
                    indicator_name=meta["indicator_name"],
                    dataset_code=dataset_code,
                    unit=meta["unit"],
                )

                rows_loaded = upsert_indicators(df=indicator_df, dataset_code=dataset_code)

                write_metadata(
                    dataset_code=dataset_code,
                    source="nomis",
                    status=ExtractionStatus.SUCCESS,
                    rows_extracted=len(raw_df),  # type: ignore[arg-type]
                    rows_loaded=rows_loaded,
                )

                results.append(
                    {
                        "Dataset": dataset_code,
                        "Rows extracted": len(raw_df),  # type: ignore[arg-type]
                        "Rows loaded": rows_loaded,
                        "Status": "OK",
                    }
                )

            except Exception as e:
                write_metadata(
                    dataset_code=dataset_code,
                    source="nomis",
                    status=ExtractionStatus.FAILED,
                    error_message=str(e)[:500],
                )
                send_failure_alert("society-education-attainment", str(e)[:500])
                results.append(
                    {
                        "Dataset": dataset_code,
                        "Rows extracted": "—",
                        "Rows loaded": "—",
                        "Status": "Failed",
                    }
                )
                raise
    finally:
        if results:
            create_table_artifact(key="load-summary", table=results, description="Load summary")
