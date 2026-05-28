"""Health Outcomes flow.

Extracts health outcome indicators from NHS Fingertips (Public Health Profiles)
for all Yorkshire LADs and loads them into the data warehouse.

Datasets loaded:

+----------+-------------------+------+---------------------------------------------+
| Code     | Indicator         | Sex  | Fingertips ID                               |
+==========+===================+======+=============================================+
| sheu75   | Under-75          | Pers | 41001 (PHOF B13)                            |
|          | preventable mort. |      |                                             |
+----------+-------------------+------+---------------------------------------------+
| sheleb_m | Life expectancy   | Male | 90366 (PHOF A01a)                           |
|          | at birth          |      |                                             |
+----------+-------------------+------+---------------------------------------------+
| sheleb_f | Life expectancy   | Fem  | 90366 (PHOF A01a) - Female dimension        |
|          | at birth          |      |                                             |
+----------+-------------------+------+---------------------------------------------+
| shehle_m | Healthy life exp. | Male | 90362 (PHOF A01a)                           |
|          | at birth          |      |                                             |
+----------+-------------------+------+---------------------------------------------+
| shehle_f | Healthy life exp. | Fem  | 90362 (PHOF A01a) - Female dimension        |
|          | at birth          |      |                                             |
+----------+-------------------+------+---------------------------------------------+
"""

from __future__ import annotations

from typing import Any

from prefect import flow
from prefect.task_runners import ThreadPoolTaskRunner

from yhovi_pipeline.db.models import ExtractionStatus
from yhovi_pipeline.tasks.extract.fingertips import (
    FINGERTIPS_REQUIRED_COLUMNS,
    extract_fingertips_indicators,
)
from yhovi_pipeline.tasks.load.database import upsert_indicators, write_metadata
from yhovi_pipeline.tasks.transform.normalise import normalise_fingertips
from yhovi_pipeline.tasks.transform.validate import validate_schema

# ---------------------------------------------------------------------------
# Dataset registry
# Each entry maps an internal dataset code to the Fingertips indicator ID,
# the sex dimension to filter on, and the metadata written to the DB.
# ---------------------------------------------------------------------------
HEALTH_DATASETS: dict[str, dict[str, Any]] = {
    "sheu75": {
        "fingertips_id": 41001,
        "indicator_id": "under75_preventable_mortality_rate",
        "indicator_name": "Under 75 mortality rate from preventable causes (per 100,000)",
        "sex_filter": "Persons",
        "age_filter": "10+ yrs",
        "unit": "per 100k",
    },
    "sheleb_m": {
        "fingertips_id": 90366,
        "indicator_id": "male_life_expectancy",
        "indicator_name": "Male life expectancy at birth (years)",
        "sex_filter": "Male",
        "age_filter": "All ages",
        "unit": "years",
    },
    "sheleb_f": {
        "fingertips_id": 90366,
        "indicator_id": "female_life_expectancy",
        "indicator_name": "Female life expectancy at birth (years)",
        "sex_filter": "Female",
        "age_filter": "All ages",
        "unit": "years",
    },
    "shehle_m": {
        "fingertips_id": 90362,
        "indicator_id": "male_healthy_life_expectancy",
        "indicator_name": "Male healthy life expectancy at birth (years)",
        "sex_filter": "Male",
        "age_filter": "All ages",
        "unit": "years",
    },
    "shehle_f": {
        "fingertips_id": 90362,
        "indicator_id": "female_healthy_life_expectancy",
        "indicator_name": "Female healthy life expectancy at birth (years)",
        "sex_filter": "Female",
        "age_filter": "All ages",
        "unit": "years",
    },
}


@flow(
    name="society-health-outcomes",
    description="Extract NHS Fingertips health outcome indicators for Yorkshire LADs.",
    retries=1,
    retry_delay_seconds=300,
    task_runner=ThreadPoolTaskRunner(max_workers=4),  # type: ignore[arg-type]
)
def health_outcomes_flow() -> None:
    """Orchestrate the health outcomes ETL pipeline.

    For each of the five health datasets, the flow:
    1. Fetches all available time-series data from the NHS Fingertips API.
    2. Validates the response schema.
    3. Normalises to the canonical Indicator schema (filters to Yorkshire LADs
       and the appropriate sex dimension).
    4. Upserts rows into the PostgreSQL data warehouse.
    5. Writes audit metadata.
    """
    for dataset_code, meta in HEALTH_DATASETS.items():
        try:
            raw_df = extract_fingertips_indicators(
                indicator_id=meta["fingertips_id"],
            )

            validated_df = validate_schema(
                df=raw_df,
                required_columns=FINGERTIPS_REQUIRED_COLUMNS,
                source="fingertips",
            )

            indicator_df = normalise_fingertips(
                df=validated_df,
                dataset_code=dataset_code,
                indicator_id=meta["indicator_id"],
                indicator_name=meta["indicator_name"],
                sex_filter=meta["sex_filter"],
                age_filter=meta["age_filter"],
                unit=meta["unit"],
            )

            rows_loaded = upsert_indicators(df=indicator_df, dataset_code=dataset_code)

            write_metadata(
                dataset_code=dataset_code,
                source="fingertips",
                status=ExtractionStatus.SUCCESS,
                rows_extracted=len(raw_df),  # type: ignore[arg-type]
                rows_loaded=rows_loaded,
            )

        except Exception as e:
            write_metadata(
                dataset_code=dataset_code,
                source="fingertips",
                status=ExtractionStatus.FAILED,
                error_message=str(e)[:500],
            )
            raise
