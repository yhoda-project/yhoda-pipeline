"""Unit tests for yhovi_pipeline.tasks.transform.normalise.

Covers all pure transform functions: date parsers, and the five normalise tasks
(normalise_to_indicator, normalise_nomis_aps, normalise_nomis_ashe,
normalise_fingertips).  Task functions are called via their ``.fn`` attribute to
invoke the underlying Python function directly, bypassing Prefect's task
machinery and avoiding the ephemeral server that Prefect otherwise spins up.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from yhovi_pipeline.tasks.transform.normalise import (
    _parse_fingertips_period,
    _parse_nomis_date,
    normalise_fingertips,
    normalise_nomis_annual,
    normalise_nomis_aps,
    normalise_nomis_ashe,
    normalise_to_indicator,
)

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_BRADFORD = "E08000032"
_CALDERDALE = "E08000033"
_LEEDS = "E08000035"
_NON_YORKSHIRE = "E09000001"  # City of London

_INDICATOR_COLS = {
    "indicator_id",
    "indicator_name",
    "geography_code",
    "geography_name",
    "geography_level",
    "lad_code",
    "lad_name",
    "reference_period",
    "value",
    "unit",
    "source",
    "dataset_code",
    "breakdown_category",
    "is_forecast",
    "forecast_model",
    "created_at",
    "updated_at",
}

# ---------------------------------------------------------------------------
# DataFrame builders
# ---------------------------------------------------------------------------


def _nomis_aps_df(**overrides: object) -> pd.DataFrame:
    """Minimal single-row Nomis APS DataFrame with valid column names."""
    data: dict[str, list] = {
        "DATE_NAME": ["Jan 2021-Dec 2021"],
        "GEOGRAPHY_NAME": ["Bradford"],
        "GEOGRAPHY_CODE": [_BRADFORD],
        "VARIABLE_NAME": ["% aged 16-64 qualified to RQF level 4 and above"],
        "VARIABLE_CODE": [1],
        "OBS_VALUE": [42.5],
    }
    data.update(overrides)  # type: ignore[arg-type]
    return pd.DataFrame(data)


def _nomis_ashe_df(**overrides: object) -> pd.DataFrame:
    """Minimal single-row Nomis ASHE DataFrame."""
    data: dict[str, list] = {
        "DATE_NAME": ["2023"],
        "GEOGRAPHY_NAME": ["Bradford"],
        "GEOGRAPHY_CODE": [_BRADFORD],
        "OBS_VALUE": [550.0],
    }
    data.update(overrides)  # type: ignore[arg-type]
    return pd.DataFrame(data)


def _nomis_annual_df(**overrides: object) -> pd.DataFrame:
    """Minimal single-row Nomis annual (4-column) DataFrame."""
    data: dict[str, list] = {
        "DATE_NAME": ["2023"],
        "GEOGRAPHY_NAME": ["Bradford"],
        "GEOGRAPHY_CODE": [_BRADFORD],
        "OBS_VALUE": [0.65],
    }
    data.update(overrides)  # type: ignore[arg-type]
    return pd.DataFrame(data)


def _fingertips_df(
    *,
    sex: str = "Persons",
    age: str = "All ages",
    category_type: object = None,
    area_code: str = _BRADFORD,
    area_name: str = "Bradford",
    time_period: str = "2021",
    value: float = 75.3,
) -> pd.DataFrame:
    """Minimal single-row Fingertips API DataFrame."""
    return pd.DataFrame(
        {
            "Sex": [sex],
            "Age": [age],
            "Category Type": [category_type],
            "Area Code": [area_code],
            "Area Name": [area_name],
            "Time period": [time_period],
            "Value": [value],
        }
    )


# ---------------------------------------------------------------------------
# _parse_nomis_date
# ---------------------------------------------------------------------------


class TestParseNomisDate:
    def test_rolling_period_returns_first_day_of_end_month(self) -> None:
        assert _parse_nomis_date("Jan 2021-Dec 2021") == date(2021, 12, 1)

    def test_rolling_period_with_spaces_around_dash(self) -> None:
        assert _parse_nomis_date("Oct 2022 - Sep 2023") == date(2023, 9, 1)

    def test_rolling_period_mid_year(self) -> None:
        assert _parse_nomis_date("Apr 2020-Mar 2021") == date(2021, 3, 1)

    def test_plain_year_returns_first_of_january(self) -> None:
        assert _parse_nomis_date("2023") == date(2023, 1, 1)

    def test_plain_year_with_surrounding_whitespace(self) -> None:
        assert _parse_nomis_date("  2019  ") == date(2019, 1, 1)

    def test_invalid_string_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Cannot parse Nomis date"):
            _parse_nomis_date("Q1 2020")


# ---------------------------------------------------------------------------
# _parse_fingertips_period
# ---------------------------------------------------------------------------


class TestParseFingertipsPeriod:
    def test_rolling_average_with_spaced_dash(self) -> None:
        assert _parse_fingertips_period("2018 - 20") == date(2020, 1, 1)

    def test_rolling_average_no_spaces(self) -> None:
        assert _parse_fingertips_period("2018-20") == date(2020, 1, 1)

    def test_financial_year(self) -> None:
        assert _parse_fingertips_period("2019/20") == date(2020, 1, 1)

    def test_financial_year_century_crossover(self) -> None:
        assert _parse_fingertips_period("1999/00") == date(2000, 1, 1)

    def test_single_year(self) -> None:
        assert _parse_fingertips_period("2021") == date(2021, 1, 1)

    def test_leading_trailing_whitespace_stripped(self) -> None:
        assert _parse_fingertips_period("  2020  ") == date(2020, 1, 1)

    def test_invalid_string_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Cannot parse Fingertips"):
            _parse_fingertips_period("not-a-date")


# ---------------------------------------------------------------------------
# normalise_nomis_aps
# ---------------------------------------------------------------------------


class TestNormaliseNomisAps:
    def test_output_has_all_required_indicator_columns(self) -> None:
        result = normalise_nomis_aps.fn(
            df=_nomis_aps_df(),
            indicator_id="qualifications_rqf4plus",
            indicator_name="% aged 16-64 qualified to RQF level 4 and above",
            dataset_code="eeeql4",
        )
        assert _INDICATOR_COLS.issubset(result.columns)

    def test_nomis_columns_mapped_to_canonical_schema(self) -> None:
        result = normalise_nomis_aps.fn(
            df=_nomis_aps_df(),
            indicator_id="qualifications_rqf4plus",
            indicator_name="% qualified to RQF4+",
            dataset_code="eeeql4",
        )
        row = result.iloc[0]
        assert row["lad_code"] == _BRADFORD
        assert row["lad_name"] == "Bradford"
        assert row["indicator_id"] == "qualifications_rqf4plus"
        assert row["source"] == "nomis"
        assert row["dataset_code"] == "eeeql4"
        assert row["unit"] == "%"
        assert row["value"] == pytest.approx(42.5)

    def test_rolling_date_parsed_to_end_month(self) -> None:
        result = normalise_nomis_aps.fn(
            df=_nomis_aps_df(DATE_NAME=["Oct 2022-Sep 2023"]),
            indicator_id="x",
            indicator_name="x",
            dataset_code="x",
        )
        assert result["reference_period"].iloc[0] == date(2023, 9, 1)

    def test_nan_obs_value_rows_dropped(self) -> None:
        df = pd.DataFrame(
            {
                "DATE_NAME": ["Jan 2021-Dec 2021", "Jan 2022-Dec 2022"],
                "GEOGRAPHY_NAME": ["Bradford", "Leeds"],
                "GEOGRAPHY_CODE": [_BRADFORD, _LEEDS],
                "VARIABLE_NAME": ["x", "x"],
                "VARIABLE_CODE": [1, 1],
                "OBS_VALUE": [42.5, None],
            }
        )
        result = normalise_nomis_aps.fn(
            df=df, indicator_id="x", indicator_name="x", dataset_code="x"
        )
        assert len(result) == 1
        assert result["lad_code"].iloc[0] == _BRADFORD

    def test_integer_date_name_coerced_to_string(self) -> None:
        """DATE_NAME arriving as an integer (e.g. 2023) must not raise AttributeError."""
        df = pd.DataFrame(
            {
                "DATE_NAME": [2023],
                "GEOGRAPHY_NAME": ["Bradford"],
                "GEOGRAPHY_CODE": [_BRADFORD],
                "VARIABLE_NAME": ["x"],
                "VARIABLE_CODE": [1],
                "OBS_VALUE": [42.5],
            }
        )
        result = normalise_nomis_aps.fn(
            df=df, indicator_id="x", indicator_name="x", dataset_code="x"
        )
        assert result["reference_period"].iloc[0] == date(2023, 1, 1)

    def test_custom_unit_propagated(self) -> None:
        result = normalise_nomis_aps.fn(
            df=_nomis_aps_df(),
            indicator_id="x",
            indicator_name="x",
            dataset_code="x",
            unit="rate",
        )
        assert result["unit"].iloc[0] == "rate"


# ---------------------------------------------------------------------------
# normalise_nomis_ashe
# ---------------------------------------------------------------------------


class TestNormaliseNomisAshe:
    def test_indicator_id_fixed_to_median_weekly_earnings(self) -> None:
        result = normalise_nomis_ashe.fn(df=_nomis_ashe_df())
        assert result["indicator_id"].iloc[0] == "median_weekly_earnings"

    def test_unit_fixed_to_gbp(self) -> None:
        result = normalise_nomis_ashe.fn(df=_nomis_ashe_df())
        assert result["unit"].iloc[0] == "£"

    def test_source_fixed_to_nomis(self) -> None:
        result = normalise_nomis_ashe.fn(df=_nomis_ashe_df())
        assert result["source"].iloc[0] == "nomis"

    def test_plain_year_date_parsed_correctly(self) -> None:
        result = normalise_nomis_ashe.fn(df=_nomis_ashe_df(DATE_NAME=["2022"]))
        assert result["reference_period"].iloc[0] == date(2022, 1, 1)

    def test_integer_date_name_coerced_to_string(self) -> None:
        """DATE_NAME arriving as an integer must not raise AttributeError."""
        df = pd.DataFrame(
            {
                "DATE_NAME": [2023],
                "GEOGRAPHY_NAME": ["Bradford"],
                "GEOGRAPHY_CODE": [_BRADFORD],
                "OBS_VALUE": [550.0],
            }
        )
        result = normalise_nomis_ashe.fn(df=df)
        assert result["reference_period"].iloc[0] == date(2023, 1, 1)

    def test_nan_obs_value_rows_dropped(self) -> None:
        df = pd.DataFrame(
            {
                "DATE_NAME": ["2022", "2023"],
                "GEOGRAPHY_NAME": ["Bradford", "Leeds"],
                "GEOGRAPHY_CODE": [_BRADFORD, _LEEDS],
                "OBS_VALUE": [550.0, None],
            }
        )
        result = normalise_nomis_ashe.fn(df=df)
        assert len(result) == 1
        assert result["lad_code"].iloc[0] == _BRADFORD


# ---------------------------------------------------------------------------
# normalise_nomis_annual
# ---------------------------------------------------------------------------


class TestNormaliseNomisAnnual:
    def test_output_has_all_required_indicator_columns(self) -> None:
        result = normalise_nomis_annual.fn(
            df=_nomis_annual_df(),
            indicator_id="jobs_per_working_age_resident",
            indicator_name="Number of Jobs per Working-Age Resident (16-64)",
            dataset_code="eejjd",
            unit="ratio",
        )
        assert _INDICATOR_COLS.issubset(result.columns)

    def test_columns_mapped_to_canonical_schema(self) -> None:
        result = normalise_nomis_annual.fn(
            df=_nomis_annual_df(),
            indicator_id="jobs_per_working_age_resident",
            indicator_name="Number of Jobs per Working-Age Resident (16-64)",
            dataset_code="eejjd",
            unit="ratio",
        )
        row = result.iloc[0]
        assert row["lad_code"] == _BRADFORD
        assert row["lad_name"] == "Bradford"
        assert row["indicator_id"] == "jobs_per_working_age_resident"
        assert row["source"] == "nomis"
        assert row["dataset_code"] == "eejjd"
        assert row["unit"] == "ratio"
        assert row["value"] == pytest.approx(0.65)

    def test_plain_year_date_parsed_correctly(self) -> None:
        result = normalise_nomis_annual.fn(
            df=_nomis_annual_df(DATE_NAME=["2022"]),
            indicator_id="x",
            indicator_name="x",
            dataset_code="x",
        )
        assert result["reference_period"].iloc[0] == date(2022, 1, 1)

    def test_integer_date_name_coerced_to_string(self) -> None:
        df = pd.DataFrame(
            {
                "DATE_NAME": [2023],
                "GEOGRAPHY_NAME": ["Bradford"],
                "GEOGRAPHY_CODE": [_BRADFORD],
                "OBS_VALUE": [0.65],
            }
        )
        result = normalise_nomis_annual.fn(
            df=df,
            indicator_id="x",
            indicator_name="x",
            dataset_code="x",
        )
        assert result["reference_period"].iloc[0] == date(2023, 1, 1)

    def test_nan_obs_value_rows_dropped(self) -> None:
        df = pd.DataFrame(
            {
                "DATE_NAME": ["2022", "2023"],
                "GEOGRAPHY_NAME": ["Bradford", "Leeds"],
                "GEOGRAPHY_CODE": [_BRADFORD, _LEEDS],
                "OBS_VALUE": [0.65, None],
            }
        )
        result = normalise_nomis_annual.fn(
            df=df,
            indicator_id="x",
            indicator_name="x",
            dataset_code="x",
        )
        assert len(result) == 1
        assert result["lad_code"].iloc[0] == _BRADFORD

    def test_unit_defaults_to_none(self) -> None:
        result = normalise_nomis_annual.fn(
            df=_nomis_annual_df(),
            indicator_id="x",
            indicator_name="x",
            dataset_code="x",
        )
        assert result["unit"].iloc[0] is None

    def test_custom_unit_propagated(self) -> None:
        result = normalise_nomis_annual.fn(
            df=_nomis_annual_df(),
            indicator_id="x",
            indicator_name="x",
            dataset_code="x",
            unit="ratio",
        )
        assert result["unit"].iloc[0] == "ratio"


# ---------------------------------------------------------------------------
# normalise_to_indicator
# ---------------------------------------------------------------------------


class TestNormaliseToIndicator:
    _SOURCE_DF = pd.DataFrame(
        {
            "gss_code": [_BRADFORD, _LEEDS],
            "area_name": ["Bradford", "Leeds"],
            "obs": [10.5, 20.0],
        }
    )

    def test_columns_mapped_to_canonical_schema(self) -> None:
        result = normalise_to_indicator.fn(
            df=self._SOURCE_DF,
            indicator_id="test_indicator",
            indicator_name="Test Indicator",
            source="ons",
            dataset_code="abc123",
            reference_period=date(2023, 1, 1),
            lad_col="gss_code",
            lad_name_col="area_name",
            value_col="obs",
            unit="units",
        )
        assert list(result["lad_code"]) == [_BRADFORD, _LEEDS]
        assert list(result["lad_name"]) == ["Bradford", "Leeds"]
        assert result["reference_period"].iloc[0] == date(2023, 1, 1)
        assert result["source"].iloc[0] == "ons"
        assert result["dataset_code"].iloc[0] == "abc123"
        assert result["unit"].iloc[0] == "units"
        assert result["value"].iloc[0] == pytest.approx(10.5)

    def test_output_has_all_required_indicator_columns(self) -> None:
        result = normalise_to_indicator.fn(
            df=self._SOURCE_DF,
            indicator_id="x",
            indicator_name="x",
            source="ons",
            dataset_code="x",
            reference_period=date(2023, 1, 1),
            lad_col="gss_code",
            lad_name_col="area_name",
            value_col="obs",
        )
        assert _INDICATOR_COLS.issubset(result.columns)

    def test_nan_value_rows_dropped(self) -> None:
        df = pd.DataFrame(
            {
                "gss_code": [_BRADFORD, _LEEDS],
                "area_name": ["Bradford", "Leeds"],
                "obs": [10.5, None],
            }
        )
        result = normalise_to_indicator.fn(
            df=df,
            indicator_id="x",
            indicator_name="x",
            source="ons",
            dataset_code="x",
            reference_period=date(2023, 1, 1),
            lad_col="gss_code",
            lad_name_col="area_name",
            value_col="obs",
        )
        assert len(result) == 1
        assert result["lad_code"].iloc[0] == _BRADFORD

    def test_unit_defaults_to_none(self) -> None:
        result = normalise_to_indicator.fn(
            df=self._SOURCE_DF,
            indicator_id="x",
            indicator_name="x",
            source="ons",
            dataset_code="x",
            reference_period=date(2023, 1, 1),
            lad_col="gss_code",
            lad_name_col="area_name",
            value_col="obs",
        )
        assert result["unit"].iloc[0] is None


# ---------------------------------------------------------------------------
# normalise_fingertips
# ---------------------------------------------------------------------------


class TestNormaliseFingertips:
    def test_sex_filter_keeps_only_matching_rows(self) -> None:
        df = pd.concat(
            [
                _fingertips_df(sex="Male", value=80.0),
                _fingertips_df(sex="Female", value=85.0),
            ]
        ).reset_index(drop=True)
        result = normalise_fingertips.fn(
            df=df,
            dataset_code="sheleb_m",
            indicator_id="life_expectancy_male",
            indicator_name="Life expectancy (male)",
            sex_filter="Male",
            age_filter="All ages",
        )
        assert len(result) == 1
        assert result["value"].iloc[0] == pytest.approx(80.0)

    def test_age_filter_keeps_only_matching_rows(self) -> None:
        df = pd.concat(
            [
                _fingertips_df(age="All ages", value=75.3),
                _fingertips_df(age="10+ yrs", value=100.0),
            ]
        ).reset_index(drop=True)
        result = normalise_fingertips.fn(
            df=df,
            dataset_code="x",
            indicator_id="x",
            indicator_name="x",
            sex_filter="Persons",
            age_filter="All ages",
        )
        assert len(result) == 1
        assert result["value"].iloc[0] == pytest.approx(75.3)

    def test_deprivation_breakdown_rows_excluded(self) -> None:
        """Rows with a non-null Category Type are deprivation breakdowns and must be dropped."""
        df = pd.concat(
            [
                _fingertips_df(category_type=None, value=75.0),
                _fingertips_df(category_type="Deprivation decile", value=60.0),
            ]
        ).reset_index(drop=True)
        result = normalise_fingertips.fn(
            df=df,
            dataset_code="x",
            indicator_id="x",
            indicator_name="x",
            sex_filter="Persons",
            age_filter="All ages",
        )
        assert len(result) == 1
        assert result["value"].iloc[0] == pytest.approx(75.0)

    def test_non_yorkshire_lads_excluded(self) -> None:
        df = pd.concat(
            [
                _fingertips_df(area_code=_BRADFORD, value=75.0),
                _fingertips_df(area_code=_NON_YORKSHIRE, area_name="London", value=80.0),
            ]
        ).reset_index(drop=True)
        result = normalise_fingertips.fn(
            df=df,
            dataset_code="x",
            indicator_id="x",
            indicator_name="x",
            sex_filter="Persons",
            age_filter="All ages",
        )
        assert len(result) == 1
        assert result["lad_code"].iloc[0] == _BRADFORD

    def test_raises_when_no_yorkshire_rows_remain(self) -> None:
        """A dataset with no Yorkshire data should raise ValueError, not silently return empty."""
        df = _fingertips_df(area_code=_NON_YORKSHIRE, area_name="London")
        with pytest.raises(ValueError, match="No Fingertips data"):
            normalise_fingertips.fn(
                df=df,
                dataset_code="sheleb_m",
                indicator_id="x",
                indicator_name="x",
                sex_filter="Persons",
                age_filter="All ages",
            )

    def test_duplicate_key_rows_deduped_keeping_last(self) -> None:
        """Two rows with the same (indicator_id, lad_code, reference_period) — keep last."""
        df = pd.concat(
            [
                _fingertips_df(value=70.0),
                _fingertips_df(value=75.0),
            ]
        ).reset_index(drop=True)
        result = normalise_fingertips.fn(
            df=df,
            dataset_code="x",
            indicator_id="life_exp",
            indicator_name="x",
            sex_filter="Persons",
            age_filter="All ages",
        )
        assert len(result) == 1
        assert result["value"].iloc[0] == pytest.approx(75.0)

    def test_rolling_average_time_period_parsed(self) -> None:
        result = normalise_fingertips.fn(
            df=_fingertips_df(time_period="2018 - 20"),
            dataset_code="x",
            indicator_id="x",
            indicator_name="x",
            sex_filter="Persons",
            age_filter="All ages",
        )
        assert result["reference_period"].iloc[0] == date(2020, 1, 1)

    def test_financial_year_time_period_parsed(self) -> None:
        result = normalise_fingertips.fn(
            df=_fingertips_df(time_period="2019/20"),
            dataset_code="x",
            indicator_id="x",
            indicator_name="x",
            sex_filter="Persons",
            age_filter="All ages",
        )
        assert result["reference_period"].iloc[0] == date(2020, 1, 1)

    def test_nan_value_rows_dropped(self) -> None:
        df = pd.concat(
            [
                _fingertips_df(area_code=_BRADFORD, value=75.0),
                _fingertips_df(area_code=_CALDERDALE, area_name="Calderdale", value=float("nan")),
            ]
        ).reset_index(drop=True)
        result = normalise_fingertips.fn(
            df=df,
            dataset_code="x",
            indicator_id="x",
            indicator_name="x",
            sex_filter="Persons",
            age_filter="All ages",
        )
        assert len(result) == 1
        assert result["lad_code"].iloc[0] == _BRADFORD

    def test_unit_propagated_to_output(self) -> None:
        result = normalise_fingertips.fn(
            df=_fingertips_df(),
            dataset_code="x",
            indicator_id="x",
            indicator_name="x",
            sex_filter="Persons",
            age_filter="All ages",
            unit="Years",
        )
        assert result["unit"].iloc[0] == "Years"

    def test_source_is_fingertips(self) -> None:
        result = normalise_fingertips.fn(
            df=_fingertips_df(),
            dataset_code="x",
            indicator_id="x",
            indicator_name="x",
            sex_filter="Persons",
            age_filter="All ages",
        )
        assert result["source"].iloc[0] == "fingertips"

    def test_output_has_all_required_indicator_columns(self) -> None:
        result = normalise_fingertips.fn(
            df=_fingertips_df(),
            dataset_code="x",
            indicator_id="x",
            indicator_name="x",
            sex_filter="Persons",
            age_filter="All ages",
        )
        assert _INDICATOR_COLS.issubset(result.columns)
