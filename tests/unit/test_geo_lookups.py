"""Unit tests for yhovi_pipeline.utils.geo_lookups."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import yhovi_pipeline.utils.geo_lookups as geo_module
from yhovi_pipeline.utils.geo_lookups import lsoa_to_lad

_SAMPLE_LOOKUP = pd.DataFrame(
    {
        "lsoa_code": ["E01000001", "E01000002", "E01000003"],
        "lsoa_name": ["Area 001A", "Area 001B", "Area 002A"],
        "msoa_code": ["E02000001", "E02000001", "E02000002"],
        "msoa_name": ["MSOA 001", "MSOA 001", "MSOA 002"],
        "lad_code": ["E06000001", "E06000001", "E06000002"],
        "lad_name": ["LAD One", "LAD One", "LAD Two"],
        "region_code": ["E12000001", "E12000001", "E12000001"],
        "region_name": ["North East", "North East", "North East"],
    }
)


@pytest.fixture(autouse=True)
def clear_geo_cache() -> None:
    geo_module.get_geo_lookup.cache_clear()
    yield
    geo_module.get_geo_lookup.cache_clear()


class TestLsoaToLad:
    def test_returns_lad_code_for_known_lsoa(self) -> None:
        with patch("yhovi_pipeline.utils.geo_lookups.get_geo_lookup", return_value=_SAMPLE_LOOKUP):
            result = lsoa_to_lad("E01000001")
        assert result == "E06000001"

    def test_returns_correct_lad_for_second_lsoa(self) -> None:
        with patch("yhovi_pipeline.utils.geo_lookups.get_geo_lookup", return_value=_SAMPLE_LOOKUP):
            result = lsoa_to_lad("E01000003")
        assert result == "E06000002"

    def test_returns_none_for_unknown_lsoa(self) -> None:
        with patch("yhovi_pipeline.utils.geo_lookups.get_geo_lookup", return_value=_SAMPLE_LOOKUP):
            result = lsoa_to_lad("E99999999")
        assert result is None

    def test_returns_none_for_empty_lookup(self) -> None:
        empty = pd.DataFrame(columns=_SAMPLE_LOOKUP.columns)
        with patch("yhovi_pipeline.utils.geo_lookups.get_geo_lookup", return_value=empty):
            result = lsoa_to_lad("E01000001")
        assert result is None


class TestGetGeoLookup:
    def _mock_engine(self) -> MagicMock:
        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        return engine

    def test_returns_dataframe(self, test_settings) -> None:
        with (
            patch(
                "yhovi_pipeline.utils.geo_lookups.create_engine", return_value=self._mock_engine()
            ),
            patch("pandas.read_sql", return_value=_SAMPLE_LOOKUP),
        ):
            result = geo_module.get_geo_lookup()
        assert isinstance(result, pd.DataFrame)

    def test_returns_expected_columns(self, test_settings) -> None:
        with (
            patch(
                "yhovi_pipeline.utils.geo_lookups.create_engine", return_value=self._mock_engine()
            ),
            patch("pandas.read_sql", return_value=_SAMPLE_LOOKUP),
        ):
            result = geo_module.get_geo_lookup()
        assert "lsoa_code" in result.columns
        assert "lad_code" in result.columns

    def test_result_is_cached(self, test_settings) -> None:
        with (
            patch(
                "yhovi_pipeline.utils.geo_lookups.create_engine", return_value=self._mock_engine()
            ) as mock_engine,
            patch("pandas.read_sql", return_value=_SAMPLE_LOOKUP),
        ):
            geo_module.get_geo_lookup()
            geo_module.get_geo_lookup()
        mock_engine.assert_called_once()
