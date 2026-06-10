"""Unit tests for yhovi_pipeline.utils.load_csv."""

from __future__ import annotations

from datetime import date
from io import StringIO
from unittest.mock import MagicMock, patch

import pandas as pd

from yhovi_pipeline.db.models import ExtractionStatus
from yhovi_pipeline.utils.load_csv import (
    DATASET_REGISTRY,
    _extract_year,
    _load_eeiratio,
    _write_csv_metadata,
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
            assert "subdomain" in DATASET_REGISTRY[code]


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


def _mock_session() -> MagicMock:
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    return session


class TestWriteCsvMetadata:
    _mod = "yhovi_pipeline.utils.load_csv"

    def test_commits_success_record(self) -> None:
        session = _mock_session()
        with patch(f"{self._mod}.Session", return_value=session):
            _write_csv_metadata(MagicMock(), "eejer", ExtractionStatus.SUCCESS, rows_loaded=10)
        session.add.assert_called_once()
        session.commit.assert_called_once()

    def test_success_record_has_correct_status(self) -> None:
        session = _mock_session()
        with patch(f"{self._mod}.Session", return_value=session):
            _write_csv_metadata(MagicMock(), "eejer", ExtractionStatus.SUCCESS, rows_loaded=10)
        record = session.add.call_args[0][0]
        assert record.extraction_status == ExtractionStatus.SUCCESS

    def test_success_record_has_rows_loaded(self) -> None:
        session = _mock_session()
        with patch(f"{self._mod}.Session", return_value=session):
            _write_csv_metadata(MagicMock(), "eejer", ExtractionStatus.SUCCESS, rows_loaded=10)
        record = session.add.call_args[0][0]
        assert record.rows_loaded == 10

    def test_failure_record_has_error_message(self) -> None:
        session = _mock_session()
        with patch(f"{self._mod}.Session", return_value=session):
            _write_csv_metadata(
                MagicMock(), "eejer", ExtractionStatus.FAILED, error_message="file not found"
            )
        record = session.add.call_args[0][0]
        assert record.error_message == "file not found"

    def test_failure_record_has_no_extracted_at(self) -> None:
        session = _mock_session()
        with patch(f"{self._mod}.Session", return_value=session):
            _write_csv_metadata(MagicMock(), "eejer", ExtractionStatus.FAILED)
        record = session.add.call_args[0][0]
        assert record.extracted_at is None

    def test_source_taken_from_registry(self) -> None:
        session = _mock_session()
        with patch(f"{self._mod}.Session", return_value=session):
            _write_csv_metadata(MagicMock(), "eejer", ExtractionStatus.SUCCESS, rows_loaded=1)
        record = session.add.call_args[0][0]
        assert record.source == "nomis"


class TestLoadAll:
    _mod = "yhovi_pipeline.utils.load_csv"

    def test_calls_load_dataset_for_each_wide_file(self, test_settings) -> None:
        with (
            patch(f"{self._mod}.load_dataset", return_value=10) as mock_wide,
            patch(f"{self._mod}.load_long_dataset", return_value=5),
            patch(f"{self._mod}._load_eeiratio", return_value=10),
            patch(f"{self._mod}._write_csv_metadata"),
            patch(f"{self._mod}.create_engine", return_value=MagicMock()),
        ):
            load_all()
        assert mock_wide.call_count > 0

    def test_calls_load_long_dataset_for_long_files(self, test_settings) -> None:
        with (
            patch(f"{self._mod}.load_dataset", return_value=10),
            patch(f"{self._mod}.load_long_dataset", return_value=5) as mock_long,
            patch(f"{self._mod}._load_eeiratio", return_value=10),
            patch(f"{self._mod}._write_csv_metadata"),
            patch(f"{self._mod}.create_engine", return_value=MagicMock()),
        ):
            load_all()
        assert mock_long.call_count > 0

    def test_continues_on_error(self, test_settings) -> None:
        with (
            patch(f"{self._mod}.load_dataset", side_effect=Exception("fail")),
            patch(f"{self._mod}.load_long_dataset", return_value=0),
            patch(f"{self._mod}._load_eeiratio", return_value=0),
            patch(f"{self._mod}._write_csv_metadata"),
            patch(f"{self._mod}.create_engine", return_value=MagicMock()),
        ):
            load_all()  # must not raise

    def test_writes_metadata_on_success(self, test_settings) -> None:
        with (
            patch(f"{self._mod}.load_dataset", return_value=10),
            patch(f"{self._mod}.load_long_dataset", return_value=5),
            patch(f"{self._mod}._load_eeiratio", return_value=10),
            patch(f"{self._mod}._write_csv_metadata") as mock_meta,
            patch(f"{self._mod}.create_engine", return_value=MagicMock()),
        ):
            load_all()
        success_calls = [
            c for c in mock_meta.call_args_list if c.args[2] == ExtractionStatus.SUCCESS
        ]
        assert len(success_calls) > 0

    def test_writes_metadata_on_failure(self, test_settings) -> None:
        with (
            patch(f"{self._mod}.load_dataset", side_effect=Exception("boom")),
            patch(f"{self._mod}.load_long_dataset", return_value=0),
            patch(f"{self._mod}._load_eeiratio", return_value=0),
            patch(f"{self._mod}._write_csv_metadata") as mock_meta,
            patch(f"{self._mod}.create_engine", return_value=MagicMock()),
        ):
            load_all()
        failed_calls = [c for c in mock_meta.call_args_list if c.args[2] == ExtractionStatus.FAILED]
        assert len(failed_calls) > 0

    def test_writes_metadata_on_long_dataset_failure(self, test_settings) -> None:
        with (
            patch(f"{self._mod}.load_dataset", return_value=10),
            patch(f"{self._mod}.load_long_dataset", side_effect=Exception("long fail")),
            patch(f"{self._mod}._load_eeiratio", return_value=10),
            patch(f"{self._mod}._write_csv_metadata") as mock_meta,
            patch(f"{self._mod}.create_engine", return_value=MagicMock()),
        ):
            load_all()
        failed_calls = [c for c in mock_meta.call_args_list if c.args[2] == ExtractionStatus.FAILED]
        assert len(failed_calls) > 0

    def test_calls_load_eeiratio(self, test_settings) -> None:
        with (
            patch(f"{self._mod}.load_dataset", return_value=10),
            patch(f"{self._mod}.load_long_dataset", return_value=5),
            patch(f"{self._mod}._load_eeiratio", return_value=10) as mock_ratio,
            patch(f"{self._mod}._write_csv_metadata"),
            patch(f"{self._mod}.create_engine", return_value=MagicMock()),
        ):
            load_all()
        mock_ratio.assert_called_once()

    def test_writes_metadata_on_eeiratio_failure(self, test_settings) -> None:
        with (
            patch(f"{self._mod}.load_dataset", return_value=10),
            patch(f"{self._mod}.load_long_dataset", return_value=5),
            patch(f"{self._mod}._load_eeiratio", side_effect=Exception("ratio fail")),
            patch(f"{self._mod}._write_csv_metadata") as mock_meta,
            patch(f"{self._mod}.create_engine", return_value=MagicMock()),
        ):
            load_all()
        failed_calls = [c for c in mock_meta.call_args_list if c.args[2] == ExtractionStatus.FAILED]
        assert any(c.args[1] == "eeiratio" for c in failed_calls)


class TestLoadEeiratio:
    _mod = "yhovi_pipeline.utils.load_csv"

    _DF10 = pd.DataFrame(
        {
            "LAD_Name": ["Bradford", "Leeds"],
            "LAD_Code": [_BRADFORD, _LEEDS],
            "2021": [300.0, 400.0],
            "2022": [310.0, 410.0],
        }
    )
    _DF80 = pd.DataFrame(
        {
            "LAD_Name": ["Bradford", "Leeds"],
            "LAD_Code": [_BRADFORD, _LEEDS],
            "2021": [600.0, 800.0],
            "2022": [620.0, 820.0],
        }
    )

    def test_returns_row_count(self, test_settings) -> None:
        engine = _mock_engine()
        with patch(f"{self._mod}.read_wide_csv", side_effect=[self._DF10, self._DF80]):
            result = _load_eeiratio(engine, "/fake/shared")
        assert result == 4  # 2 LADs x 2 years

    def test_ratio_is_eei80_divided_by_eei10(self, test_settings) -> None:
        engine = _mock_engine()
        records: list[dict] = []

        def capture_execute(stmt):
            records.extend(
                stmt.compile(compile_kwargs={"literal_binds": True}).string if False else []
            )

        with patch(f"{self._mod}.read_wide_csv", side_effect=[self._DF10, self._DF80]):
            _load_eeiratio(engine, "/fake/shared")

        conn = engine.begin.return_value.__enter__.return_value
        conn.execute.assert_called_once()

    def test_returns_zero_for_no_yorkshire_lads(self, test_settings) -> None:
        df10 = pd.DataFrame({"LAD_Name": ["London"], "LAD_Code": [_NON_YORKSHIRE], "2021": [300.0]})
        df80 = pd.DataFrame({"LAD_Name": ["London"], "LAD_Code": [_NON_YORKSHIRE], "2021": [600.0]})
        engine = _mock_engine()
        with patch(f"{self._mod}.read_wide_csv", side_effect=[df10, df80]):
            result = _load_eeiratio(engine, "/fake/shared")
        assert result == 0

    def test_indicator_id_is_earnings_p80_p10_ratio(self, test_settings) -> None:
        assert DATASET_REGISTRY["eeiratio"]["indicator_id"] == "earnings_p80_p10_ratio"

    def test_eei10_and_eei80_in_registry(self) -> None:
        assert "eei10" in DATASET_REGISTRY
        assert "eei80" in DATASET_REGISTRY
        assert DATASET_REGISTRY["eei10"]["unit"] == "£/week"
        assert DATASET_REGISTRY["eei80"]["unit"] == "£/week"
