"""Unit tests for yhovi_pipeline.tasks.extract.nomis."""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from yhovi_pipeline.tasks.extract.nomis import (
    APS_VARIABLES,
    BASE_URL,
    _build_nomis_url,
    _fetch_nomis_csv,
    extract_aps,
    extract_ashe,
    extract_jobs_density,
)

_SAMPLE_CSV = "date_name,geography_name,geography_code,obs_value\n2023,Bradford,E08000032,75.3\n"
_APS_CSV = (
    "date_name,geography_name,geography_code,variable_name,variable_code,obs_value\n"
    "2023,Bradford,E08000032,Employment Rate,45,72.1\n"
)


def _ok_response(text: str = _SAMPLE_CSV) -> MagicMock:
    mock = MagicMock()
    mock.text = text
    mock.raise_for_status = MagicMock()
    return mock


class TestBuildNomisUrl:
    def test_url_starts_with_base_url(self) -> None:
        url = _build_nomis_url("NM_17_5", geography=["E08000032"])
        assert url.startswith(BASE_URL)

    def test_url_contains_dataset(self) -> None:
        url = _build_nomis_url("NM_17_5", geography=["E08000032"])
        assert "NM_17_5" in url

    def test_geography_codes_included(self) -> None:
        url = _build_nomis_url("NM_99_1", geography=["E08000032", "E08000033"])
        assert "E08000032" in url
        assert "E08000033" in url

    def test_geography_codes_joined_with_comma(self) -> None:
        url = _build_nomis_url("NM_99_1", geography=["E08000032", "E08000033"])
        assert "E08000032,E08000033" in url

    def test_default_time_is_latest(self) -> None:
        url = _build_nomis_url("NM_99_1", geography=["E08000032"])
        assert "time=latest" in url

    def test_custom_time_included(self) -> None:
        url = _build_nomis_url("NM_99_1", geography=["E08000032"], time="2023-12")
        assert "time=2023-12" in url

    def test_select_included_when_provided(self) -> None:
        url = _build_nomis_url("NM_99_1", geography=["E08000032"], select="date_name,obs_value")
        assert "select=date_name,obs_value" in url

    def test_select_omitted_when_not_provided(self) -> None:
        url = _build_nomis_url("NM_99_1", geography=["E08000032"])
        assert "select=" not in url

    def test_uid_included_when_provided(self) -> None:
        url = _build_nomis_url("NM_99_1", geography=["E08000032"], uid="my-api-key")
        assert "uid=my-api-key" in url

    def test_uid_omitted_when_not_provided(self) -> None:
        url = _build_nomis_url("NM_99_1", geography=["E08000032"])
        assert "uid=" not in url

    def test_list_extra_param_joined_with_comma(self) -> None:
        url = _build_nomis_url("NM_17_5", geography=["E08000032"], variable=[45, 84])
        assert "variable=45,84" in url

    def test_scalar_extra_param_included(self) -> None:
        url = _build_nomis_url("NM_99_1", geography=["E08000032"], pay=1)
        assert "pay=1" in url

    def test_returns_csv_endpoint(self) -> None:
        url = _build_nomis_url("NM_99_1", geography=["E08000032"])
        assert ".data.csv" in url


class TestFetchNomisCsv:
    def test_returns_dataframe(self) -> None:
        with patch("requests.get", return_value=_ok_response()):
            result = _fetch_nomis_csv("http://example.com/api")
        assert isinstance(result, pd.DataFrame)

    def test_row_count_matches_csv(self) -> None:
        with patch("requests.get", return_value=_ok_response()):
            result = _fetch_nomis_csv("http://example.com/api")
        assert len(result) == 1

    def test_http_error_propagates(self) -> None:
        mock = MagicMock()
        mock.raise_for_status.side_effect = requests.HTTPError("500")
        with patch("requests.get", return_value=mock), pytest.raises(requests.HTTPError):
            _fetch_nomis_csv("http://example.com/api")


class TestExtractAps:
    def test_unknown_variable_raises_value_error(self, test_settings) -> None:
        with pytest.raises(ValueError, match="Unknown APS variable"):
            extract_aps.fn(variable="not_a_variable")

    def test_error_message_lists_valid_keys(self, test_settings) -> None:
        with pytest.raises(ValueError, match="employment_rate"):
            extract_aps.fn(variable="bad_key")

    def test_returns_dataframe_for_valid_variable(self, test_settings) -> None:
        with patch(
            "yhovi_pipeline.tasks.extract.nomis._fetch_nomis_csv",
            return_value=pd.read_csv(StringIO(_APS_CSV)),
        ):
            result = extract_aps.fn(variable="employment_rate")
        assert isinstance(result, pd.DataFrame)

    def test_all_aps_variables_are_valid(self, test_settings) -> None:
        for var in APS_VARIABLES:
            with patch(
                "yhovi_pipeline.tasks.extract.nomis._fetch_nomis_csv",
                return_value=pd.read_csv(StringIO(_APS_CSV)),
            ):
                result = extract_aps.fn(variable=var)
            assert isinstance(result, pd.DataFrame)


class TestExtractAshe:
    def test_returns_dataframe(self, test_settings) -> None:
        with patch(
            "yhovi_pipeline.tasks.extract.nomis._fetch_nomis_csv",
            return_value=pd.read_csv(StringIO(_SAMPLE_CSV)),
        ):
            result = extract_ashe.fn()
        assert isinstance(result, pd.DataFrame)

    def test_custom_time_accepted(self, test_settings) -> None:
        with patch(
            "yhovi_pipeline.tasks.extract.nomis._fetch_nomis_csv",
            return_value=pd.read_csv(StringIO(_SAMPLE_CSV)),
        ):
            result = extract_ashe.fn(time="2022-12")
        assert isinstance(result, pd.DataFrame)


class TestExtractJobsDensity:
    def test_returns_dataframe(self, test_settings) -> None:
        with patch(
            "yhovi_pipeline.tasks.extract.nomis._fetch_nomis_csv",
            return_value=pd.read_csv(StringIO(_SAMPLE_CSV)),
        ):
            result = extract_jobs_density.fn()
        assert isinstance(result, pd.DataFrame)

    def test_custom_time_accepted(self, test_settings) -> None:
        with patch(
            "yhovi_pipeline.tasks.extract.nomis._fetch_nomis_csv",
            return_value=pd.read_csv(StringIO(_SAMPLE_CSV)),
        ):
            result = extract_jobs_density.fn(time="2020,2021,2022")
        assert isinstance(result, pd.DataFrame)
