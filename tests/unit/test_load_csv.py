"""Unit tests for yhovi_pipeline.utils.load_csv."""

from __future__ import annotations

from datetime import date
from io import StringIO
from unittest.mock import MagicMock, patch

import pandas as pd

from yhovi_pipeline.utils.load_csv import (
    DATASET_REGISTRY,
    _extract_year,
    load_all,
    load_dataset,
    load_long_dataset,
    read_wide_csv,
    wide_to_long,
)

_BRADFORD = "E08000032"
_LEEDS = "E08000035"
_NON_YORKSHIRE = "E09000001"

_WIDE_CSV = f"""LAD_Name,LAD_Code,2021,2022,2023
Bradford,{_BRADFORD},70.1,71.2,72.3
Leeds,{_LEEDS},75.0,76.0,77.0
London,{_NON_YORKSHIRE},80.0,81.0,82.0
"""


def _wide_df() -> pd.DataFrame:
    return pd.read_csv(StringIO(_WIDE_CSV))


class TestExtractYear:
    def test_plain_four_digit_year(self) -> None:
        assert _extract_year("2022") == 2022

    def test_date_range_returns_last_year(self) -> None:
        assert _extract_year("April 2011 to March 2012") == 2012

    def test_year_at_end_of_string(self) -> None:
        assert _extract_year("FY 2020-21 ending 2021") == 2021

    def test_single_year_in_longer_string(self) -> None:
        assert _extract_year("Survey year 2019") == 2019

    def test_numeric_column_name(self) -> None:
        assert _extract_year(2023) == 2023


class TestReadWideCsv:
    def test_returns_dataframe(self, tmp_path) -> None:
        p = tmp_path / "test.csv"
        p.write_text(_WIDE_CSV)
        result = read_wide_csv(str(p))
        assert isinstance(result, pd.DataFrame)

    def test_correct_row_count(self, tmp_path) -> None:
        p = tmp_path / "test.csv"
        p.write_text(_WIDE_CSV)
        result = read_wide_csv(str(p))
        assert len(result) == 3

    def test_columns_preserved(self, tmp_path) -> None:
        p = tmp_path / "test.csv"
        p.write_text(_WIDE_CSV)
        result = read_wide_csv(str(p))
        assert "LAD_Code" in result.columns
        assert "2021" in result.columns


class TestWideToLong:
    def test_returns_dataframe(self) -> None:
        result = wide_to_long(_wide_df(), "eejer")
        assert isinstance(result, pd.DataFrame)

    def test_non_yorkshire_lads_excluded(self) -> None:
        result = wide_to_long(_wide_df(), "eejer")
        assert _NON_YORKSHIRE not in result["lad_code"].values

    def test_yorkshire_lads_retained(self) -> None:
        result = wide_to_long(_wide_df(), "eejer")
        assert _BRADFORD in result["lad_code"].values
        assert _LEEDS in result["lad_code"].values

    def test_output_has_one_row_per_lad_per_year(self) -> None:
        result = wide_to_long(_wide_df(), "eejer")
        assert len(result) == 6  # 2 Yorkshire LADs x 3 years

    def test_reference_period_is_date(self) -> None:
        result = wide_to_long(_wide_df(), "eejer")
        assert result["reference_period"].iloc[0] == date(2021, 1, 1)

    def test_indicator_id_from_registry(self) -> None:
        result = wide_to_long(_wide_df(), "eejer")
        assert all(result["indicator_id"] == "employment_rate")

    def test_indicator_name_from_registry(self) -> None:
        result = wide_to_long(_wide_df(), "eejer")
        assert all(result["indicator_name"] == "Employment rate")

    def test_unit_from_registry(self) -> None:
        result = wide_to_long(_wide_df(), "eejer")
        assert all(result["unit"] == "%")

    def test_source_from_registry(self) -> None:
        result = wide_to_long(_wide_df(), "eejer")
        assert all(result["source"] == "nomis")

    def test_geography_level_is_lad(self) -> None:
        result = wide_to_long(_wide_df(), "eejer")
        assert all(result["geography_level"] == "lad")

    def test_lad_code_equals_geography_code(self) -> None:
        result = wide_to_long(_wide_df(), "eejer")
        assert (result["lad_code"] == result["geography_code"]).all()

    def test_nan_values_dropped(self) -> None:
        csv_with_nan = f"LAD_Name,LAD_Code,2021\nBradford,{_BRADFORD},\n"
        df = pd.read_csv(StringIO(csv_with_nan))
        result = wide_to_long(df, "eejer")
        assert len(result) == 0

    def test_breakdown_category_is_empty_string(self) -> None:
        result = wide_to_long(_wide_df(), "eejer")
        assert all(result["breakdown_category"] == "")

    def test_is_forecast_is_false(self) -> None:
        result = wide_to_long(_wide_df(), "eejer")
        assert all(result["is_forecast"] == False)  # noqa: E712

    def test_value_is_numeric(self) -> None:
        result = wide_to_long(_wide_df(), "eejer")
        assert result["value"].dtype == float

    def test_normalises_lad_name_x_column(self) -> None:
        df = pd.read_csv(StringIO(_WIDE_CSV)).rename(columns={"LAD_Name": "LAD_Name.x"})
        result = wide_to_long(df, "eejer")
        assert len(result) > 0

    def test_all_dataset_codes_in_registry_are_valid(self) -> None:
        for code in DATASET_REGISTRY:
            assert "indicator_id" in DATASET_REGISTRY[code]
            assert "indicator_name" in DATASET_REGISTRY[code]
            assert "unit" in DATASET_REGISTRY[code]
            assert "source" in DATASET_REGISTRY[code]


def _mock_engine() -> MagicMock:
    engine = MagicMock()
    conn = MagicMock()
    engine.begin.return_value.__enter__ = MagicMock(return_value=conn)
    engine.begin.return_value.__exit__ = MagicMock(return_value=False)
    return engine


class TestLoadDataset:
    def test_returns_row_count(self, tmp_path, test_settings) -> None:
        p = tmp_path / "test.csv"
        p.write_text(_WIDE_CSV)
        with patch("yhovi_pipeline.utils.load_csv.create_engine", return_value=_mock_engine()):
            result = load_dataset(str(p), "eejer")
        assert result == 6  # 2 Yorkshire LADs, 3 years

    def test_returns_zero_for_no_yorkshire_rows(self, tmp_path, test_settings) -> None:
        csv = f"LAD_Name,LAD_Code,2021\nLondon,{_NON_YORKSHIRE},80.0\n"
        p = tmp_path / "test.csv"
        p.write_text(csv)
        with patch("yhovi_pipeline.utils.load_csv.create_engine", return_value=_mock_engine()):
            result = load_dataset(str(p), "eejer")
        assert result == 0

    def test_executes_against_engine(self, tmp_path, test_settings) -> None:
        p = tmp_path / "test.csv"
        p.write_text(_WIDE_CSV)
        engine = _mock_engine()
        conn = engine.begin.return_value.__enter__.return_value
        with patch("yhovi_pipeline.utils.load_csv.create_engine", return_value=engine):
            load_dataset(str(p), "eejer")
        conn.execute.assert_called_once()


class TestLoadLongDataset:
    _LONG_CSV = (
        f"LAD24CD,LAD24NM,Year,Value\n"
        f"{_BRADFORD},Bradford,2022,123.4\n"
        f"{_LEEDS},Leeds,2022,456.7\n"
        f"{_NON_YORKSHIRE},London,2022,999.9\n"
    )

    def test_returns_row_count(self, tmp_path, test_settings) -> None:
        p = tmp_path / "test.csv"
        p.write_text(self._LONG_CSV)
        with patch("yhovi_pipeline.utils.load_csv.create_engine", return_value=_mock_engine()):
            result = load_long_dataset(str(p), "ebegvala", "LAD24CD", "LAD24NM", "Year", "Value")
        assert result == 2

    def test_non_yorkshire_excluded(self, tmp_path, test_settings) -> None:
        csv = f"LAD24CD,LAD24NM,Year,Value\n{_NON_YORKSHIRE},London,2022,999.9\n"
        p = tmp_path / "test.csv"
        p.write_text(csv)
        with patch("yhovi_pipeline.utils.load_csv.create_engine", return_value=_mock_engine()):
            result = load_long_dataset(str(p), "ebegvala", "LAD24CD", "LAD24NM", "Year", "Value")
        assert result == 0

    def test_returns_zero_for_all_nan_values(self, tmp_path, test_settings) -> None:
        csv = f"LAD24CD,LAD24NM,Year,Value\n{_BRADFORD},Bradford,2022,\n"
        p = tmp_path / "test.csv"
        p.write_text(csv)
        with patch("yhovi_pipeline.utils.load_csv.create_engine", return_value=_mock_engine()):
            result = load_long_dataset(str(p), "ebegvala", "LAD24CD", "LAD24NM", "Year", "Value")
        assert result == 0


class TestLoadAll:
    def test_calls_load_dataset_for_each_wide_file(self, test_settings) -> None:
        with (
            patch("yhovi_pipeline.utils.load_csv.load_dataset", return_value=10) as mock_wide,
            patch("yhovi_pipeline.utils.load_csv.load_long_dataset", return_value=5),
        ):
            load_all()
        assert mock_wide.call_count > 0

    def test_calls_load_long_dataset_for_long_files(self, test_settings) -> None:
        with (
            patch("yhovi_pipeline.utils.load_csv.load_dataset", return_value=10),
            patch("yhovi_pipeline.utils.load_csv.load_long_dataset", return_value=5) as mock_long,
        ):
            load_all()
        assert mock_long.call_count > 0

    def test_continues_on_error(self, test_settings) -> None:
        with (
            patch("yhovi_pipeline.utils.load_csv.load_dataset", side_effect=Exception("fail")),
            patch("yhovi_pipeline.utils.load_csv.load_long_dataset", return_value=0),
        ):
            load_all()  # must not raise
