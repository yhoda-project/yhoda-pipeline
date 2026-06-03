"""Unit tests for yhovi_pipeline.tasks.extract.fingertips."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from yhovi_pipeline.tasks.extract.fingertips import (
    ENGLAND_PARENT_CODE,
    LAD_AREA_TYPE_ID,
    extract_fingertips_indicators,
)

_SAMPLE_CSV = (
    "Indicator ID,Indicator Name,Area Code,Area Name,Sex,Age,Category Type,Time period,Value\n"
    "90366,Life expectancy,E06000001,Hartlepool,Male,All ages,,2020 - 22,78.5\n"
    "90366,Life expectancy,E06000002,Middlesbrough,Male,All ages,,2020 - 22,77.1\n"
)


def _mock_response(csv_text: str = _SAMPLE_CSV) -> MagicMock:
    mock = MagicMock()
    mock.text = csv_text
    mock.raise_for_status = MagicMock()
    return mock


class TestExtractFingertipsIndicators:
    def test_returns_dataframe(self) -> None:
        with patch("requests.get", return_value=_mock_response()):
            result = extract_fingertips_indicators.fn(indicator_id=90366)
        assert isinstance(result, pd.DataFrame)

    def test_row_count_matches_csv(self) -> None:
        with patch("requests.get", return_value=_mock_response()):
            result = extract_fingertips_indicators.fn(indicator_id=90366)
        assert len(result) == 2

    def test_url_contains_indicator_id(self) -> None:
        with patch("requests.get", return_value=_mock_response()) as mock_get:
            extract_fingertips_indicators.fn(indicator_id=90366)
        url = mock_get.call_args[0][0]
        assert "indicator_ids=90366" in url

    def test_url_contains_area_type_id(self) -> None:
        with patch("requests.get", return_value=_mock_response()) as mock_get:
            extract_fingertips_indicators.fn(indicator_id=90366)
        url = mock_get.call_args[0][0]
        assert f"area_type_id={LAD_AREA_TYPE_ID}" in url

    def test_url_contains_england_parent_code(self) -> None:
        with patch("requests.get", return_value=_mock_response()) as mock_get:
            extract_fingertips_indicators.fn(indicator_id=90366)
        url = mock_get.call_args[0][0]
        assert ENGLAND_PARENT_CODE in url

    def test_http_error_propagates(self) -> None:
        mock = MagicMock()
        mock.raise_for_status.side_effect = requests.HTTPError("404")
        with patch("requests.get", return_value=mock), pytest.raises(requests.HTTPError):
            extract_fingertips_indicators.fn(indicator_id=99999)

    def test_dataframe_contains_indicator_id_column(self) -> None:
        with patch("requests.get", return_value=_mock_response()):
            result = extract_fingertips_indicators.fn(indicator_id=90366)
        assert "Indicator ID" in result.columns

    def test_dataframe_contains_area_code_column(self) -> None:
        with patch("requests.get", return_value=_mock_response()):
            result = extract_fingertips_indicators.fn(indicator_id=90366)
        assert "Area Code" in result.columns

    def test_dataframe_contains_value_column(self) -> None:
        with patch("requests.get", return_value=_mock_response()):
            result = extract_fingertips_indicators.fn(indicator_id=90366)
        assert "Value" in result.columns
