"""Unit tests for yhovi_pipeline.utils loader utilities.

Covers seed_geo_lookup, load_jobs, load_neighbourhoods, and load_industry.
All database and filesystem I/O is mocked.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd

from yhovi_pipeline.utils.load_industry import (
    _is_gss_code,
    _normalise_grouping_level,
    load_industry_business,
    load_industry_kpi,
)
from yhovi_pipeline.utils.load_jobs import load_jobs
from yhovi_pipeline.utils.load_neighbourhoods import _parse_time, _slugify, load_neighbourhoods
from yhovi_pipeline.utils.seed_geo_lookup import load_geo_lookup

_BRADFORD = "E08000032"
_LONDON = "E09000001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_engine() -> MagicMock:
    engine = MagicMock()
    conn = MagicMock()
    engine.begin.return_value.__enter__ = MagicMock(return_value=conn)
    engine.begin.return_value.__exit__ = MagicMock(return_value=False)
    return engine


# ---------------------------------------------------------------------------
# seed_geo_lookup
# ---------------------------------------------------------------------------

_GEO_CSV = pd.DataFrame(
    {
        "LSOA21CD": ["E01000001", "E99000001"],
        "LSOA21NM": ["Bradford LSOA 001", "London LSOA 001"],
        "MSOA21CD": ["E02000001", "E02999001"],
        "MSOA21NM": ["Bradford MSOA 001", "London MSOA 001"],
        "LAD23CD": [_BRADFORD, _LONDON],
        "LAD23NM": ["Bradford", "London"],
    }
)

_GEO_CSV_NO_YORKSHIRE = pd.DataFrame(
    {
        "LSOA21CD": ["E99000001"],
        "LSOA21NM": ["London LSOA"],
        "MSOA21CD": ["E02999001"],
        "MSOA21NM": ["London MSOA"],
        "LAD23CD": [_LONDON],
        "LAD23NM": ["London"],
    }
)


class TestLoadGeoLookup:
    def test_returns_yorkshire_lad_count(self, test_settings) -> None:
        engine = _mock_engine()
        with (
            patch("yhovi_pipeline.utils.seed_geo_lookup.create_engine", return_value=engine),
            patch("pandas.read_csv", return_value=_GEO_CSV),
        ):
            result = load_geo_lookup(path="dummy.csv")
        assert result == 1  # only Bradford row

    def test_returns_zero_when_no_yorkshire_lads(self, test_settings) -> None:
        engine = _mock_engine()
        with (
            patch("yhovi_pipeline.utils.seed_geo_lookup.create_engine", return_value=engine),
            patch("pandas.read_csv", return_value=_GEO_CSV_NO_YORKSHIRE),
        ):
            result = load_geo_lookup(path="dummy.csv")
        assert result == 0

    def test_executes_upsert_statement(self, test_settings) -> None:
        engine = _mock_engine()
        conn = engine.begin.return_value.__enter__.return_value
        with (
            patch("yhovi_pipeline.utils.seed_geo_lookup.create_engine", return_value=engine),
            patch("pandas.read_csv", return_value=_GEO_CSV),
        ):
            load_geo_lookup(path="dummy.csv")
        conn.execute.assert_called_once()


# ---------------------------------------------------------------------------
# load_jobs
# ---------------------------------------------------------------------------

_JOBS_CSV = pd.DataFrame(
    {
        "LSOA11CD": ["E01000001", "E99000001"],
        "LSOA11NM": ["Bradford LSOA", "London LSOA"],
        "MSOA_Code": ["E02000001", "E02999001"],
        "MSOA11NM": ["Bradford MSOA", "London MSOA"],
        "Area..MSOA.": ["Bradford MSOA (HCL)", None],
        "LAD_Code": [_BRADFORD, _LONDON],
        "Local.Authority": ["Bradford", "London"],
        "Year": [2022, 2022],
        "SIC_Code": [1, 2],
        "SIC": ["Agriculture", "Mining"],
        "Section": ["A", "B"],
        "Division": ["01", "05"],
        "Group": ["01.1", "05.1"],
        "Employees": ["100", "200"],
    }
)


class TestLoadJobs:
    def test_returns_yorkshire_row_count(self, test_settings) -> None:
        engine = _mock_engine()
        with (
            patch("yhovi_pipeline.utils.load_jobs.create_engine", return_value=engine),
            patch("pandas.read_csv", return_value=_JOBS_CSV),
        ):
            result = load_jobs(path="dummy.csv")
        assert result == 1  # only Bradford row

    def test_returns_zero_for_non_yorkshire_data(self, test_settings) -> None:
        df = _JOBS_CSV[_JOBS_CSV["LAD_Code"] == _LONDON].copy()
        engine = _mock_engine()
        with (
            patch("yhovi_pipeline.utils.load_jobs.create_engine", return_value=engine),
            patch("pandas.read_csv", return_value=df),
        ):
            result = load_jobs(path="dummy.csv")
        assert result == 0

    def test_executes_batch_upsert(self, test_settings) -> None:
        engine = _mock_engine()
        conn = engine.begin.return_value.__enter__.return_value
        with (
            patch("yhovi_pipeline.utils.load_jobs.create_engine", return_value=engine),
            patch("pandas.read_csv", return_value=_JOBS_CSV),
        ):
            load_jobs(path="dummy.csv")
        conn.execute.assert_called()


# ---------------------------------------------------------------------------
# load_neighbourhoods
# ---------------------------------------------------------------------------

_LSOA_CSV = pd.DataFrame(
    {
        "lsoa_code": ["E01000001", "E99000001"],
        "lsoa_name": ["Bradford LSOA", "London LSOA"],
        "Time": ["31/12/2021", "31/12/2021"],
        "Value": ["55.3", "70.1"],
        "Indicator": ["Deprivation Score", "Deprivation Score"],
        "Domain": ["Health", "Health"],
    }
)

_GEO_LOOKUP = pd.DataFrame(
    {
        "lsoa_code": ["E01000001"],
        "lad_code": [_BRADFORD],
        "lad_name": ["Bradford"],
    }
)


class TestSluggify:
    def test_lowercases_and_replaces_spaces(self) -> None:
        assert _slugify("Total Population (People)") == "total_population_people"

    def test_strips_leading_trailing_underscores(self) -> None:
        result = _slugify("  Score  ")
        assert not result.startswith("_")
        assert not result.endswith("_")


class TestParseTime:
    def test_parses_dd_mm_yyyy_format(self) -> None:
        from datetime import date

        assert _parse_time("31/12/2021") == date(2021, 12, 31)

    def test_parses_01_01_2000(self) -> None:
        from datetime import date

        assert _parse_time("01/01/2000") == date(2000, 1, 1)


class TestLoadNeighbourhoods:
    def test_returns_yorkshire_row_count(self, test_settings) -> None:
        engine = _mock_engine()
        with (
            patch("yhovi_pipeline.utils.load_neighbourhoods.create_engine", return_value=engine),
            patch("pandas.read_csv", return_value=_LSOA_CSV),
            patch(
                "yhovi_pipeline.utils.load_neighbourhoods.get_geo_lookup",
                return_value=_GEO_LOOKUP,
            ),
        ):
            result = load_neighbourhoods(path="dummy.csv")
        assert result == 1  # only Bradford LSOA has geo_lookup match

    def test_returns_zero_when_no_geo_match(self, test_settings) -> None:
        empty_geo = pd.DataFrame(columns=["lsoa_code", "lad_code", "lad_name"])
        engine = _mock_engine()
        with (
            patch("yhovi_pipeline.utils.load_neighbourhoods.create_engine", return_value=engine),
            patch("pandas.read_csv", return_value=_LSOA_CSV),
            patch(
                "yhovi_pipeline.utils.load_neighbourhoods.get_geo_lookup",
                return_value=empty_geo,
            ),
        ):
            result = load_neighbourhoods(path="dummy.csv")
        assert result == 0

    def test_returns_zero_for_nan_values(self, test_settings) -> None:
        lsoa_nan = _LSOA_CSV.copy()
        lsoa_nan["lsoa_code"] = ["E01000001", "E99000001"]
        lsoa_nan["Value"] = [None, None]
        engine = _mock_engine()
        with (
            patch("yhovi_pipeline.utils.load_neighbourhoods.create_engine", return_value=engine),
            patch("pandas.read_csv", return_value=lsoa_nan),
            patch(
                "yhovi_pipeline.utils.load_neighbourhoods.get_geo_lookup",
                return_value=_GEO_LOOKUP,
            ),
        ):
            result = load_neighbourhoods(path="dummy.csv")
        assert result == 0

    def test_executes_batch_upsert(self, test_settings) -> None:
        engine = _mock_engine()
        conn = engine.begin.return_value.__enter__.return_value
        with (
            patch("yhovi_pipeline.utils.load_neighbourhoods.create_engine", return_value=engine),
            patch("pandas.read_csv", return_value=_LSOA_CSV),
            patch(
                "yhovi_pipeline.utils.load_neighbourhoods.get_geo_lookup",
                return_value=_GEO_LOOKUP,
            ),
        ):
            load_neighbourhoods(path="dummy.csv")
        conn.execute.assert_called()


# ---------------------------------------------------------------------------
# load_industry helpers
# ---------------------------------------------------------------------------

_MSOA_LOOKUP = pd.DataFrame(
    {
        "lsoa_code": ["E01000001"],
        "msoa_code": ["E02000001"],
        "msoa_name": ["Bradford MSOA"],
        "lad_code": [_BRADFORD],
        "lad_name": ["Bradford"],
        "region_code": ["E12000003"],
        "region_name": ["Yorkshire and The Humber"],
    }
)

_GRANULAR_CSV = pd.DataFrame(
    {
        "MSOA": ["E02000001", "E02999001"],
        "MSOA11NM": ["Bradford MSOA", "London MSOA"],
        "LAD23NM": ["Bradford", "London"],
        "Industry": ["Agriculture", "Mining"],
        "Turnover": ["0 to 49k", "0 to 49k"],
        "Year": [2022, 2022],
        "Business": [10, 5],
    }
)

_KPI_CSV = pd.DataFrame(
    {
        "Grouping_Level": ["LAD", "Yorkshire"],
        "Year": [2022, 2022],
        "LAD23NM": ["Bradford", "Yorkshire"],
        "MSOA": ["", ""],
        "Industry": ["All", "All"],
        "Turnover": ["All", "All"],
        "Business": [100, 500],
        "Business_Lag3": [90, 450],
        "Pct_Change_3Y": [11.1, 11.1],
        "Business_Lag8": [80, 400],
        "Pct_Change_8Y": [25.0, 25.0],
    }
)


class TestIsGssCode:
    def test_returns_true_for_gss_codes(self) -> None:
        series = pd.Series(["E02000001", "E02000002"])
        assert _is_gss_code(series) is True

    def test_returns_false_for_names(self) -> None:
        series = pd.Series(["Bradford MSOA", "Leeds MSOA"])
        assert _is_gss_code(series) is False

    def test_returns_false_for_empty_series(self) -> None:
        assert _is_gss_code(pd.Series([], dtype=str)) is False


class TestNormaliseGroupingLevel:
    def test_lowercases_and_replaces_spaces(self) -> None:
        assert _normalise_grouping_level("Grouping Level") == "grouping_level"

    def test_already_lowercase_unchanged(self) -> None:
        assert _normalise_grouping_level("lad") == "lad"


class TestLoadIndustryBusiness:
    def test_returns_yorkshire_row_count(self, test_settings) -> None:
        engine = _mock_engine()
        with (
            patch("yhovi_pipeline.utils.load_industry.create_engine", return_value=engine),
            patch("pandas.read_csv", return_value=_GRANULAR_CSV),
            patch(
                "yhovi_pipeline.utils.load_industry.get_geo_lookup",
                return_value=_MSOA_LOOKUP,
            ),
        ):
            result = load_industry_business(path="dummy.csv")
        assert result == 1

    def test_returns_zero_when_no_yorkshire_rows(self, test_settings) -> None:
        df = _GRANULAR_CSV[_GRANULAR_CSV["LAD23NM"] == "London"].copy()
        engine = _mock_engine()
        with (
            patch("yhovi_pipeline.utils.load_industry.create_engine", return_value=engine),
            patch("pandas.read_csv", return_value=df),
            patch(
                "yhovi_pipeline.utils.load_industry.get_geo_lookup",
                return_value=_MSOA_LOOKUP,
            ),
        ):
            result = load_industry_business(path="dummy.csv")
        assert result == 0

    def test_executes_batch_upsert(self, test_settings) -> None:
        engine = _mock_engine()
        conn = engine.begin.return_value.__enter__.return_value
        with (
            patch("yhovi_pipeline.utils.load_industry.create_engine", return_value=engine),
            patch("pandas.read_csv", return_value=_GRANULAR_CSV),
            patch(
                "yhovi_pipeline.utils.load_industry.get_geo_lookup",
                return_value=_MSOA_LOOKUP,
            ),
        ):
            load_industry_business(path="dummy.csv")
        conn.execute.assert_called()


class TestLoadIndustryKpi:
    def test_runs_without_error(self, test_settings) -> None:
        engine = _mock_engine()
        with (
            patch("yhovi_pipeline.utils.load_industry.create_engine", return_value=engine),
            patch("pandas.read_csv", return_value=_KPI_CSV),
            patch(
                "yhovi_pipeline.utils.load_industry.get_geo_lookup",
                return_value=_MSOA_LOOKUP,
            ),
        ):
            load_industry_kpi(path="dummy.csv")

    def test_returns_row_count(self, test_settings) -> None:
        engine = _mock_engine()
        with (
            patch("yhovi_pipeline.utils.load_industry.create_engine", return_value=engine),
            patch("pandas.read_csv", return_value=_KPI_CSV),
            patch(
                "yhovi_pipeline.utils.load_industry.get_geo_lookup",
                return_value=_MSOA_LOOKUP,
            ),
        ):
            result = load_industry_kpi(path="dummy.csv")
        assert isinstance(result, int)

    def test_executes_batch_upsert(self, test_settings) -> None:
        engine = _mock_engine()
        conn = engine.begin.return_value.__enter__.return_value
        with (
            patch("yhovi_pipeline.utils.load_industry.create_engine", return_value=engine),
            patch("pandas.read_csv", return_value=_KPI_CSV),
            patch(
                "yhovi_pipeline.utils.load_industry.get_geo_lookup",
                return_value=_MSOA_LOOKUP,
            ),
        ):
            load_industry_kpi(path="dummy.csv")
        conn.execute.assert_called()
