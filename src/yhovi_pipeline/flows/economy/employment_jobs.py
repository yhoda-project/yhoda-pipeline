"""Employment & Jobs flow.

Extracts employment count and rate data from NOMIS (BRES / APS datasets)
for all Yorkshire LADs and loads them into the data warehouse.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from prefect import flow
from prefect.artifacts import create_table_artifact
from prefect.task_runners import ThreadPoolTaskRunner

from yhovi_pipeline.db.models import ExtractionStatus
from yhovi_pipeline.tasks.extract.nomis import extract_aps, extract_jobs_density
from yhovi_pipeline.tasks.load.database import upsert_indicators, write_metadata
from yhovi_pipeline.tasks.transform.normalise import normalise_nomis_annual, normalise_nomis_aps
from yhovi_pipeline.tasks.transform.validate import validate_schema
from yhovi_pipeline.utils.notify import send_failure_alert

# Map APS variable keys to dataset metadata for the indicator table.
APS_DATASETS: dict[str, dict[str, str]] = {
    "employment_rate": {
        "indicator_id": "employment_rate",
        "indicator_name": "Employment rate",
        "dataset_code": "eejer",
        "unit": "%",
    },
    "unemployment_rate": {
        "indicator_id": "unemployment_rate",
        "indicator_name": "Unemployment rate",
        "dataset_code": "eejur",
        "unit": "%",
    },
    "self_employment_rate": {
        "indicator_id": "self_employment_rate",
        "indicator_name": "Self-employment rate",
        "dataset_code": "eejse",
        "unit": "%",
    },
    "econ_inactive_rate": {
        "indicator_id": "econ_inactive_want_job",
        "indicator_name": "Percentage of economically inactive who want a job",
        "dataset_code": "eejeir",
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

NOMIS_ANNUAL_COLUMNS = [
    "DATE_NAME",
    "GEOGRAPHY_NAME",
    "GEOGRAPHY_CODE",
    "OBS_VALUE",
]


@flow(
    name="economy-employment-jobs",
    flow_run_name=lambda **_: datetime.now().strftime("%B %Y") + " - Economy: Employment & Jobs",
    description="Extract employment and jobs data from NOMIS for Yorkshire LADs.",
    retries=1,
    retry_delay_seconds=300,
    task_runner=ThreadPoolTaskRunner(max_workers=4),  # type: ignore[arg-type]
)
def employment_jobs_flow(time: str = "latest") -> None:
    """Orchestrate the employment & jobs ETL pipeline.

    Extracts APS indicators from NOMIS, validates, normalises to the
    Indicator schema, and upserts into the PostgreSQL data warehouse.

    Args:
        time: Nomis time parameter - "latest" for most recent period,
            or a range like "2004-12-2024-12" for historical data.
    """
    results: list[dict[str, Any]] = []
    try:
        for variable_key, meta in APS_DATASETS.items():
            dataset_code = meta["dataset_code"]

            try:
                # Extract
                raw_df = extract_aps(variable=variable_key, time=time)

                # Validate
                validated_df = validate_schema(
                    df=raw_df,
                    required_columns=NOMIS_APS_COLUMNS,
                    source="nomis",
                )

                # Transform
                indicator_df = normalise_nomis_aps(
                    df=validated_df,
                    indicator_id=meta["indicator_id"],
                    indicator_name=meta["indicator_name"],
                    dataset_code=dataset_code,
                    unit=meta["unit"],
                )

                # Load
                rows_loaded = upsert_indicators(df=indicator_df, dataset_code=dataset_code)

                # Audit
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
                send_failure_alert("economy-employment-jobs", str(e)[:500])
                results.append(
                    {
                        "Dataset": dataset_code,
                        "Rows extracted": "-",
                        "Rows loaded": "-",
                        "Status": "Failed",
                    }
                )
                raise

        # Jobs Density (eejjd - ONS NM_57_1, pre-calculated ratio)
        dataset_code = "eejjd"
        try:
            raw_df = extract_jobs_density(time=time)

            validated_df = validate_schema(
                df=raw_df,
                required_columns=NOMIS_ANNUAL_COLUMNS,
                source="nomis",
            )

            indicator_df = normalise_nomis_annual(
                df=validated_df,
                indicator_id="jobs_per_working_age_resident",
                indicator_name="Number of Jobs per Working-Age Resident (16-64)",
                dataset_code=dataset_code,
                unit="ratio",
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
            send_failure_alert("economy-employment-jobs", str(e)[:500])
            results.append(
                {
                    "Dataset": dataset_code,
                    "Rows extracted": "-",
                    "Rows loaded": "-",
                    "Status": "Failed",
                }
            )
            raise

    finally:
        if results:
            create_table_artifact(key="load-summary", table=results, description="Load summary")
