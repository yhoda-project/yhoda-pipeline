"""Load preprocessed wide-format CSVs into the indicator table.

Reads the YHODA team's existing preprocessed CSV files (wide format with
columns: LAD_Name, LAD_Code, <year1>, <year2>, ...) and transforms them
into the long-format Indicator schema for upserting into PostgreSQL.

Usage (from the VM)::

    export $(grep -v '^#' .env | xargs)
    uv run python -m yhovi_pipeline.utils.load_csv

Or import and call ``load_dataset()`` directly.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime

import pandas as pd
from sqlalchemy import Engine, create_engine
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from yhovi_pipeline.config import YORKSHIRE_LAD_CODES, get_settings
from yhovi_pipeline.db.models import DatasetMetadata, ExtractionStatus, Indicator

# Map dataset codes to their indicator metadata.
# indicator_id is a short machine-readable key; indicator_name is human-readable.
DATASET_REGISTRY: dict[str, dict[str, str]] = {
    "eejer": {
        "indicator_id": "employment_rate",
        "indicator_name": "Employment rate",
        "unit": "%",
        "source": "nomis",
        "subdomain": "Employment and Jobs",
    },
    "eejse": {
        "indicator_id": "self_employment_rate",
        "indicator_name": "Self-employment rate",
        "unit": "%",
        "source": "nomis",
        "subdomain": "Employment and Jobs",
    },
    "eejur": {
        "indicator_id": "unemployment_rate",
        "indicator_name": "Unemployment rate",
        "unit": "%",
        "source": "nomis",
        "subdomain": "Employment and Jobs",
    },
    "eejeir": {
        "indicator_id": "econ_inactive_want_job",
        "indicator_name": "Percentage of economically inactive who want a job",
        "unit": "%",
        "source": "nomis",
        "subdomain": "Employment and Jobs",
    },
    "eejjd": {
        "indicator_id": "jobs_per_working_age_resident",
        "indicator_name": "Number of Jobs per Working-Age Resident (16-64)",
        "unit": "ratio",
        "source": "nomis",
        "subdomain": "Employment and Jobs",
    },
    "ebebs": {
        "indicator_id": "businesses_per_10k",
        "indicator_name": "Number of Business Counts per 10,000 inhabitants",
        "unit": "per 10k",
        "source": "ons",
        "subdomain": "Business and Economy",
    },
    "ebegva": {
        "indicator_id": "gva_millions",
        "indicator_name": "Gross Value Added (£ millions)",
        "unit": "£m",
        "source": "ons",
        "subdomain": "Business and Economy",
    },
    "sda65": {
        "indicator_id": "pct_aged_65_plus",
        "indicator_name": "Percentage of Individuals aged 65+",
        "unit": "%",
        "source": "ons",
        "subdomain": "Demographics",
    },
    "sdau18": {
        "indicator_id": "pct_aged_under_18",
        "indicator_name": "Percentage of Individuals under 18 years old",
        "unit": "%",
        "source": "ons",
        "subdomain": "Demographics",
    },
    "sdpop": {
        "indicator_id": "total_population",
        "indicator_name": "Total population",
        "unit": "persons",
        "source": "ons",
        "subdomain": "Demographics",
    },
    "ses19l3": {
        "indicator_id": "level3_qualifications_pct",
        "indicator_name": "Percentage of 19 year olds achieving Level 3 qualifications",
        "unit": "%",
        "source": "dfe",
        "subdomain": "Education and Skills",
    },
    "sesfsm": {
        "indicator_id": "free_school_meals_pct",
        "indicator_name": "Percentage of pupils eligible for free school meals",
        "unit": "%",
        "source": "dfe",
        "subdomain": "Education and Skills",
    },
    "sespg94": {
        "indicator_id": "gcse_english_maths_94_pct",
        "indicator_name": "Percentage of pupils achieving grades 9 to 4 in GCSE English and Maths",
        "unit": "%",
        "source": "dfe",
        "subdomain": "Education and Skills",
    },
    "swa150plus": {
        "indicator_id": "physically_active_150plus_pct",
        "indicator_name": "Percentage of adults active for 150+ minutes per week",
        "unit": "%",
        "source": "sport_england",
        "subdomain": "Wellbeing",
    },
    "swa30minus": {
        "indicator_id": "physically_inactive_pct",
        "indicator_name": "Percentage of adults inactive in sports (under 30 minutes per week)",
        "unit": "%",
        "source": "sport_england",
        "subdomain": "Wellbeing",
    },
    "swa30": {
        "indicator_id": "fairly_active_pct",
        "indicator_name": "Percentage of fairly active adults (30-149 minutes per week)",
        "unit": "%",
        "source": "sport_england",
        "subdomain": "Wellbeing",
    },
    "swls": {
        "indicator_id": "mean_life_satisfaction",
        "indicator_name": "Mean life satisfaction score (0-10)",
        "unit": "score",
        "source": "ons",
        "subdomain": "Wellbeing",
    },
    "swwl": {
        "indicator_id": "mean_worthwhile_score",
        "indicator_name": "Mean worthwhile score (0-10)",
        "unit": "score",
        "source": "ons",
        "subdomain": "Wellbeing",
    },
    "scsv": {
        "indicator_id": "violence_offences_per_1k",
        "indicator_name": "Number of violence against the person offences per 1,000 population",
        "unit": "per 1k",
        "source": "ons",
        "subdomain": "Community Safety",
    },
    "scst": {
        "indicator_id": "theft_offences_per_1k",
        "indicator_name": "Number of theft offences per 1,000 population",
        "unit": "per 1k",
        "source": "ons",
        "subdomain": "Community Safety",
    },
    "eeigwe": {
        "indicator_id": "avg_weekly_earnings",
        "indicator_name": "Average weekly earnings (£)",
        "unit": "£",
        "source": "ashe",
        "subdomain": "Earnings and Income",
    },
    "scpo": {
        "indicator_id": "public_order_offences_per_1k",
        "indicator_name": "Public order offences per 1,000 people",
        "unit": "per 1k",
        "source": "ons",
        "subdomain": "Crime",
    },
    "scp": {
        "indicator_id": "volunteering_sports_pct",
        "indicator_name": "Percentage of adults volunteering in sports or physical activity",
        "unit": "%",
        "source": "sport_england",
        "subdomain": "Civic Participation",
    },
    "shomee": {
        "indicator_id": "median_energy_efficiency_score",
        "indicator_name": "Median energy efficiency score of households",
        "unit": "score",
        "source": "beis",
        "subdomain": "Housing",
    },
    "eeicli": {
        "indicator_id": "children_low_income_per_10k",
        "indicator_name": "Children in relative low income households per 10,000",
        "unit": "per 10k",
        "source": "dwp",
        "subdomain": "Earnings and Income",
    },
    "ewrkg": {
        "indicator_id": "household_waste_kg_per_head",
        "indicator_name": "Household waste (kg) collected per head of population",
        "unit": "kg",
        "source": "defra",
        "subdomain": "Waste and Recycling",
    },
    "ewrr": {
        "indicator_id": "household_waste_recycled_pct",
        "indicator_name": "Percentage of household waste sent for reuse, recycling or composting",
        "unit": "%",
        "source": "defra",
        "subdomain": "Waste and Recycling",
    },
    "scasla": {
        "indicator_id": "avg_download_speed_mbit",
        "indicator_name": "Average broadband download speed (Mbit/s)",
        "unit": "Mbit/s",
        "source": "ofcom",
        "subdomain": "Connectivity",
    },
    "scpna": {
        "indicator_id": "pct_no_30mbit_broadband",
        "indicator_name": "Percentage of premises without 30Mbit/s+ download speeds",
        "unit": "%",
        "source": "ofcom",
        "subdomain": "Connectivity",
    },
    "shohar": {
        "indicator_id": "housing_affordability_ratio",
        "indicator_name": "Housing affordability ratio (median house price to median earnings)",
        "unit": "ratio",
        "source": "ons",
        "subdomain": "Housing",
    },
    "shoahc": {
        "indicator_id": "affordable_housing_completions_per_100k",
        "indicator_name": "Affordable housing completions per 100,000 population",
        "unit": "per 100k",
        "source": "dluhc",
        "subdomain": "Housing",
    },
    "shohwl": {
        "indicator_id": "housing_waiting_list_pct",
        "indicator_name": "Proportion of households on the housing waiting list",
        "unit": "%",
        "source": "dluhc",
        "subdomain": "Housing",
    },
    "ebebcr": {
        "indicator_id": "business_churn_rate_per_10k",
        "indicator_name": "Registered business churn rate per 10,000 population",
        "unit": "per 10k",
        "source": "ons",
        "subdomain": "Business and Economy",
    },
    "ebegvala": {
        "indicator_id": "gva_per_la",
        "indicator_name": "Gross Value Added by local authority (£ millions)",
        "unit": "£m",
        "source": "ons",
        "subdomain": "Business and Economy",
    },
    "eejpip": {
        "indicator_id": "disability_benefits_per_100k",
        "indicator_name": "Number of people with disability benefits (PIP) per 100,000 residents",
        "unit": "per 100k",
        "source": "dwp",
        "subdomain": "Employment and Jobs",
    },
    "sheu75": {
        "indicator_id": "under75_preventable_mortality_rate",
        "indicator_name": "Under 75 mortality rate from preventable causes (per 100,000)",
        "unit": "per 100k",
        "source": "phe",
        "subdomain": "Health",
    },
    "sheleb_m": {
        "indicator_id": "male_life_expectancy",
        "indicator_name": "Male life expectancy at birth (years)",
        "unit": "years",
        "source": "phe",
        "subdomain": "Health",
    },
    "sheleb_f": {
        "indicator_id": "female_life_expectancy",
        "indicator_name": "Female life expectancy at birth (years)",
        "unit": "years",
        "source": "phe",
        "subdomain": "Health",
    },
    "shehle_m": {
        "indicator_id": "male_healthy_life_expectancy",
        "indicator_name": "Male healthy life expectancy at birth (years)",
        "unit": "years",
        "source": "phe",
        "subdomain": "Health",
    },
    "shehle_f": {
        "indicator_id": "female_healthy_life_expectancy",
        "indicator_name": "Female healthy life expectancy at birth (years)",
        "unit": "years",
        "source": "phe",
        "subdomain": "Health",
    },
    "enz_co2": {
        "indicator_id": "enz_co2",
        "indicator_name": "Tonnes of CO2 emissions per capita per year",
        "unit": "tonnes",
        "source": "beis",
        "subdomain": "Net Zero",
    },
    "enz_ch4": {
        "indicator_id": "enz_ch4",
        "indicator_name": "Tonnes of methane emissions (CO2e) per capita per year",
        "unit": "tonnes CO2e",
        "source": "beis",
        "subdomain": "Net Zero",
    },
    "enz_n2o": {
        "indicator_id": "enz_n2o",
        "indicator_name": "Tonnes of nitrous oxide emissions (CO2e) per capita per year",
        "unit": "tonnes CO2e",
        "source": "beis",
        "subdomain": "Net Zero",
    },
    # -----------------------------------------------------------------------
    # Employment and Jobs - APS: economically inactive breakdown
    # EEJPEI splits into two indicators on disk (eejpei_w / eejpei_dw).
    # -----------------------------------------------------------------------
    "eejpei_w": {
        "indicator_id": "econ_inactive_want_job_pct",
        "indicator_name": "Percentage of economically inactive who want a job",
        "unit": "%",
        "source": "nomis",
        "subdomain": "Employment and Jobs",
    },
    "eejpei_dw": {
        "indicator_id": "econ_inactive_not_want_job_pct",
        "indicator_name": "Percentage of economically inactive who do not want a job",
        "unit": "%",
        "source": "nomis",
        "subdomain": "Employment and Jobs",
    },
}


def read_wide_csv(path: str) -> pd.DataFrame:
    """Read a preprocessed wide-format CSV.

    Expected columns: LAD_Name, LAD_Code, <year1>, <year2>, ...

    Returns:
        DataFrame in wide format.
    """
    return pd.read_csv(path)


def _extract_year(col: str) -> int:
    """Extract the last 4-digit year from a column name.

    Handles plain years ("2022") and date-range strings
    ("April 2011 to March 2012" → 2012).
    """
    years = re.findall(r"\b(\d{4})\b", str(col))
    return int(years[-1])


def wide_to_long(df: pd.DataFrame, dataset_code: str) -> pd.DataFrame:
    """Transform a wide-format DataFrame into the Indicator long format.

    Args:
        df: Wide DataFrame with LAD_Name, LAD_Code, and year columns.
        dataset_code: Key into DATASET_REGISTRY.

    Returns:
        Long DataFrame with columns matching the Indicator table.
    """
    meta = DATASET_REGISTRY[dataset_code]

    # Normalise non-standard column names produced by some preprocessing scripts
    df = df.rename(
        columns={
            "LAD_Name.x": "LAD_Name",
            "Area Names": "LAD_Name",
            "Area Codes": "LAD_Code",
        }
    )

    year_cols = [c for c in df.columns if c not in ("LAD_Name", "LAD_Code")]

    long = df.melt(
        id_vars=["LAD_Name", "LAD_Code"],
        value_vars=year_cols,
        var_name="year",
        value_name="value",
    )

    long["year"] = long["year"].apply(_extract_year)
    long = long[long["LAD_Code"].isin(YORKSHIRE_LAD_CODES)]
    long = long.dropna(subset=["value"])

    now = datetime.now(UTC)
    lad_codes = long["LAD_Code"]
    lad_names = long["LAD_Name"]
    result = pd.DataFrame(
        {
            "indicator_id": meta["indicator_id"],
            "indicator_name": meta["indicator_name"],
            "geography_code": lad_codes,
            "geography_name": lad_names,
            "geography_level": "lad",
            "lad_code": lad_codes,
            "lad_name": lad_names,
            "reference_period": long["year"].apply(lambda y: date(y, 1, 1)),
            "value": long["value"].astype(float),
            "unit": meta["unit"],
            "source": meta["source"],
            "dataset_code": dataset_code,
            "breakdown_category": "",
            "is_forecast": False,
            "forecast_model": None,
            "created_at": now,
            "updated_at": now,
        }
    )

    return result


def load_dataset(path: str, dataset_code: str) -> int:
    """Load a single preprocessed CSV into the indicator table.

    Args:
        path: Path to the wide-format CSV file.
        dataset_code: Key into DATASET_REGISTRY.

    Returns:
        Number of rows upserted.
    """
    settings = get_settings()
    engine = create_engine(settings.database_url.get_secret_value())

    df = read_wide_csv(path)
    long = wide_to_long(df, dataset_code)

    records = long.to_dict(orient="records")
    if not records:
        print(f"  No records for {dataset_code}")
        return 0

    stmt = pg_insert(Indicator).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=[
            "indicator_id",
            "geography_code",
            "reference_period",
            "breakdown_category",
        ],
        set_={
            "indicator_name": stmt.excluded.indicator_name,
            "geography_name": stmt.excluded.geography_name,
            "geography_level": stmt.excluded.geography_level,
            "lad_code": stmt.excluded.lad_code,
            "lad_name": stmt.excluded.lad_name,
            "value": stmt.excluded.value,
            "unit": stmt.excluded.unit,
            "source": stmt.excluded.source,
            "dataset_code": stmt.excluded.dataset_code,
            "updated_at": stmt.excluded.updated_at,
        },
    )

    with engine.begin() as conn:
        conn.execute(stmt)

    print(f"  Upserted {len(records)} rows for {dataset_code}")
    return len(records)


# Files to load: (dataset_code, relative path from data_preprocessing dir)
CSV_FILES: list[tuple[str, str]] = [
    ("eejer", "eejer/eejer_preprocessed_v4.csv"),
    ("eejse", "eejse/eejse_preprocessed_v2.csv"),
    ("eejur", "eejur/eejur_preprocessed_v2.csv"),
    ("eejeir", "eejeir/eejeir_preprocessed_v3.csv"),
    ("eejjd", "eejjd/eejjd_preprocessed_v3.csv"),
    ("ebebs", "ebebs/ebebs_v1_preprocessed.csv"),
    ("ebegva", "ebegva/ebegva_v1_preprocessed.csv"),
    ("sda65", "sda65/sda65_preprocessed_v1_5.csv"),
    ("sdau18", "sdau18/sdau18_preprocessed_v1_4.csv"),
    ("sdpop", "sdpop/sdpop_preprocessed_v1_4.csv"),
    ("ses19l3", "ses19l3/ses19l3_preprocessed_v1_9.csv"),
    ("sesfsm", "sesfsm/sesfsm_preprocessing_v1_2.csv"),
    ("sespg94", "sespg94/sespg94_preprocessing_v1_2.csv"),
    ("swa150plus", "swa150plus/swa150plus_preprocessing_v1_2.csv"),
    ("swa30minus", "swa30minus/swa30minus_preprocessing_v1_3.csv"),
    ("swa30", "swa30/swa30_preprocessing_v1_3.csv"),
    ("swls", "swls/swls_preprocessing_v1_1.csv"),
    ("swwl", "swwl/swwl_preprocessing_v1_1.csv"),
    ("scsv", "scsv/scsv_preprocessing_v1_4.csv"),
    ("eeigwe", "eeigwe/eeigwe_preprocessing_v2.csv"),
    ("scpo", "scpo/scpo_preprocessing_v1_4.csv"),
    ("scp", "scp/scp_preprocessing_v1_3.csv"),
    ("shomee", "shomee/shomee_preprocessing_v1_1.csv"),
    ("eeicli", "eeicli/eeicli_preprocessed_v1_5.csv"),
    ("scst", "scst/scst_preprocessing_v1_4.csv"),
    ("ewrkg", "ewrkg/ewrkg_preprocessing_v1_7.csv"),
    ("ewrr", "ewrr/ewrr_preprocessing_v1_7.csv"),
    ("scasla", "scasla/scasla_preprocessing_v1_1.csv"),
    ("scpna", "scpna/scpna_preprocessing_v1_1.csv"),
    ("shohar", "shohar/shohar_preprocessed_v1_1.csv"),
    ("shoahc", "shoahc/shoahc_preprocessing_v1_2.csv"),
    ("shohwl", "shohwl/shohwl_preprocessing_v1_2.csv"),
    ("eejpip", "eejpip/eejpip_preprocessing_v1_5.csv"),
    ("sheu75", "sheu75/sheu75_preprocessed_v1_2.csv"),
    ("sheleb_m", "sheleb/sheleb_m/sheleb_m_preprocessing_v1_1.csv"),
    ("sheleb_f", "sheleb/sheleb_f/sheleb_f_preprocessing_v1_1.csv"),
    ("shehle_m", "shehle/shehle_m/shehle_m_preprocessing_v1_1.csv"),
    ("shehle_f", "shehle/shehle_f/shehle_f_preprocessing_v1_1.csv"),
    ("enz_co2", "enz/carbondioxide/enz_carbondioxide_preprocessed_v1_7.csv"),
    ("enz_ch4", "enz/methane/enz_methane_preprocessed_v1_7.csv"),
    ("enz_n2o", "enz/nitrousoxide/enz_nitrousoxide_preprocessed_v1_7.csv"),
    ("eejpei_w", "eejpei/eejpei_w/eejpei_w_preprocessed_v3.csv"),
    ("eejpei_dw", "eejpei/eejpei_dw/eejpei_dw_preprocessed_v3.csv"),
]

_OBS_SUBDIR = "1_Yorkshire_Vitality_Observatory/data_preprocessing"


# Long-format files: (dataset_code, relative path, lad_code_col, lad_name_col, year_col, value_col)
LONG_CSV_FILES: list[tuple[str, str, str, str, str, str]] = [
    (
        "ebebcr",
        "ebebcr/ebebcr_preprocessed_v2.csv",
        "LAD23CD",
        "LocalAuthority",
        "Year",
        "ChurnRate_per_10000",
    ),
    ("ebegvala", "ebegvala/ebegvala_v1_3.csv", "LAD24CD", "LAD24NM", "Year", "Value"),
]


def load_long_dataset(
    path: str,
    dataset_code: str,
    lad_code_col: str,
    lad_name_col: str,
    year_col: str,
    value_col: str,
) -> int:
    """Load a long-format CSV (one row per LAD per year) into the indicator table.

    Args:
        path: Path to the CSV file.
        dataset_code: Key into DATASET_REGISTRY.
        lad_code_col: Column name for LAD GSS code.
        lad_name_col: Column name for LAD name.
        year_col: Column name for the year.
        value_col: Column name for the indicator value.

    Returns:
        Number of rows upserted.
    """
    meta = DATASET_REGISTRY[dataset_code]
    settings = get_settings()
    engine = create_engine(settings.database_url.get_secret_value())

    df = pd.read_csv(path)
    df = df[df[lad_code_col].isin(YORKSHIRE_LAD_CODES)]
    df = df.dropna(subset=[value_col])

    now = datetime.now(UTC)
    lad_codes = df[lad_code_col].values
    lad_names = df[lad_name_col].values
    result = pd.DataFrame(
        {
            "indicator_id": meta["indicator_id"],
            "indicator_name": meta["indicator_name"],
            "geography_code": lad_codes,
            "geography_name": lad_names,
            "geography_level": "lad",
            "lad_code": lad_codes,
            "lad_name": lad_names,
            "reference_period": df[year_col].apply(lambda y: date(int(y), 1, 1)),
            "value": pd.to_numeric(df[value_col], errors="coerce"),
            "unit": meta["unit"],
            "source": meta["source"],
            "dataset_code": dataset_code,
            "breakdown_category": "",
            "is_forecast": False,
            "forecast_model": None,
            "created_at": now,
            "updated_at": now,
        }
    )
    result = result.dropna(subset=["value"])

    records = result.to_dict(orient="records")
    if not records:
        print(f"  No records for {dataset_code}")
        return 0

    stmt = pg_insert(Indicator).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=[
            "indicator_id",
            "geography_code",
            "reference_period",
            "breakdown_category",
        ],
        set_={
            "indicator_name": stmt.excluded.indicator_name,
            "geography_name": stmt.excluded.geography_name,
            "geography_level": stmt.excluded.geography_level,
            "lad_code": stmt.excluded.lad_code,
            "lad_name": stmt.excluded.lad_name,
            "value": stmt.excluded.value,
            "unit": stmt.excluded.unit,
            "source": stmt.excluded.source,
            "dataset_code": stmt.excluded.dataset_code,
            "updated_at": stmt.excluded.updated_at,
        },
    )

    with engine.begin() as conn:
        conn.execute(stmt)

    print(f"  Upserted {len(records)} rows for {dataset_code}")
    return len(records)


def _write_csv_metadata(
    engine: Engine,
    dataset_code: str,
    status: ExtractionStatus,
    rows_loaded: int | None = None,
    error_message: str | None = None,
) -> None:
    source = DATASET_REGISTRY[dataset_code]["source"]
    now = datetime.now(UTC)
    record = DatasetMetadata(
        dataset_code=dataset_code,
        source=source,
        extraction_status=status,
        rows_extracted=rows_loaded,
        rows_loaded=rows_loaded,
        extracted_at=now if status == ExtractionStatus.SUCCESS else None,
        loaded_at=now if rows_loaded else None,
        error_message=error_message,
        created_at=now,
    )
    with Session(engine) as session:
        session.add(record)
        session.commit()


def load_all() -> None:
    """Load all available preprocessed CSVs into the database."""
    shared = get_settings().shared_drive_path
    if not shared:
        raise RuntimeError(
            "SHARED_DRIVE_PATH is not set. Add it to .env before running this script."
        )
    base_path = f"{shared}/{_OBS_SUBDIR}"
    engine = create_engine(get_settings().database_url.get_secret_value())

    total = 0
    for dataset_code, rel_path in CSV_FILES:
        path = f"{base_path}/{rel_path}"
        print(f"Loading {dataset_code} from {path}...")
        try:
            count = load_dataset(path, dataset_code)
            total += count
            _write_csv_metadata(engine, dataset_code, ExtractionStatus.SUCCESS, rows_loaded=count)
        except Exception as e:
            print(f"  ERROR loading {dataset_code}: {e}")
            _write_csv_metadata(
                engine, dataset_code, ExtractionStatus.FAILED, error_message=str(e)[:500]
            )

    for dataset_code, rel_path, lad_code_col, lad_name_col, year_col, value_col in LONG_CSV_FILES:
        path = f"{base_path}/{rel_path}"
        print(f"Loading {dataset_code} from {path}...")
        try:
            count = load_long_dataset(
                path, dataset_code, lad_code_col, lad_name_col, year_col, value_col
            )
            total += count
            _write_csv_metadata(engine, dataset_code, ExtractionStatus.SUCCESS, rows_loaded=count)
        except Exception as e:
            print(f"  ERROR loading {dataset_code}: {e}")
            _write_csv_metadata(
                engine, dataset_code, ExtractionStatus.FAILED, error_message=str(e)[:500]
            )

    print(f"\nDone. Total rows upserted: {total}")


if __name__ == "__main__":
    load_all()
