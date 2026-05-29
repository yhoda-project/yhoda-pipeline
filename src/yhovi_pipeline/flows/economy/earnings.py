"""Earnings flow.

Extracts median gross weekly earnings from NOMIS (ASHE dataset NM_99_1)
for all Yorkshire LADs and loads them into the data warehouse.
"""

from __future__ import annotations

from prefect import flow
from prefect.task_runners import ThreadPoolTaskRunner

from yhovi_pipeline.db.models import ExtractionStatus
from yhovi_pipeline.tasks.extract.nomis import extract_ashe
from yhovi_pipeline.tasks.load.database import upsert_indicators, write_metadata
from yhovi_pipeline.tasks.transform.normalise import normalise_nomis_ashe
from yhovi_pipeline.tasks.transform.validate import validate_schema
from yhovi_pipeline.utils.notify import send_failure_alert

DATASET_CODE = "eejpay"

ASHE_COLUMNS = ["DATE_NAME", "GEOGRAPHY_NAME", "GEOGRAPHY_CODE", "OBS_VALUE"]


@flow(
    name="economy-earnings",
    description="Extract median gross weekly earnings from NOMIS ASHE for Yorkshire LADs.",
    retries=1,
    retry_delay_seconds=300,
    task_runner=ThreadPoolTaskRunner(max_workers=4),  # type: ignore[arg-type]
)
def earnings_flow(time: str = "latest") -> None:
    """Orchestrate the earnings ETL pipeline.

    Extracts ASHE median gross weekly pay from NOMIS, validates,
    normalises to the Indicator schema, and upserts into the PostgreSQL
    data warehouse.

    Args:
        time: Nomis time parameter — "latest" for most recent year, or a
            range like "2010,2011,...,2024" for historical data.
    """
    try:
        raw_df = extract_ashe(time=time)

        validated_df = validate_schema(
            df=raw_df,
            required_columns=ASHE_COLUMNS,
            source="nomis",
        )

        indicator_df = normalise_nomis_ashe(
            df=validated_df,
            dataset_code=DATASET_CODE,
        )

        rows_loaded = upsert_indicators(df=indicator_df, dataset_code=DATASET_CODE)

        write_metadata(
            dataset_code=DATASET_CODE,
            source="nomis",
            status=ExtractionStatus.SUCCESS,
            rows_extracted=len(raw_df),  # type: ignore[arg-type]
            rows_loaded=rows_loaded,
        )

    except Exception as e:
        write_metadata(
            dataset_code=DATASET_CODE,
            source="nomis",
            status=ExtractionStatus.FAILED,
            error_message=str(e)[:500],
        )
        send_failure_alert("economy-earnings", str(e)[:500])
        raise
