"""Unit tests for yhovi_pipeline.tasks.extract.dwp."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from yhovi_pipeline.config import YORKSHIRE_LAD_CODES
from yhovi_pipeline.tasks.extract.dwp import (
    _CIL_DATABASE,
    _CIL_DATE_FIELD,
    _CIL_LA_VALUESET,
    _CIL_MEASURE,
    _extract_dwp_table,
    _fetch_date_items,
    _flatten_cube,
    _gss_from_uri,
    _headers,
    _post_table,
    browse_stat_xplore_schema,
    extract_children_low_income,
    extract_pip_claimants,
)


def _cube_response(
    date_labels: list[str],
    geo_labels: list[str],
    geo_uris: list[str],
    values: list[list[float | None]],
) -> dict:
    return {
        "fields": [
            {
                "label": "Date",
                "items": [
                    {"labels": [label], "uris": [f"uri:date:{label}"]} for label in date_labels
                ],
            },
            {
                "label": "Geography",
                "items": [
                    {"labels": [label], "uris": [uri]}
                    for label, uri in zip(geo_labels, geo_uris, strict=False)
                ],
            },
        ],
        "cubes": {"some_measure": {"values": values}},
    }


class TestGssFromUri:
    def test_extracts_gss_code_from_standard_uri(self) -> None:
        uri = "str:val:PIP_Monthly_new:V_F_PIP_MONTHLY:COA_CODE:E08000032"
        assert _gss_from_uri(uri) == "E08000032"

    def test_extracts_code_from_short_uri(self) -> None:
        assert _gss_from_uri("str:val:E06000061") == "E06000061"

    def test_works_for_single_segment(self) -> None:
        assert _gss_from_uri("E08000032") == "E08000032"

    def test_different_gss_codes(self) -> None:
        assert _gss_from_uri("prefix:E09000001") == "E09000001"


class TestHeaders:
    def test_returns_dict_with_api_key(self) -> None:
        result = _headers("my-test-key")
        assert result["APIKey"] == "my-test-key"

    def test_returns_dict_with_content_type(self) -> None:
        result = _headers("my-test-key")
        assert result["Content-Type"] == "application/json"

    def test_api_key_value_is_used_verbatim(self) -> None:
        result = _headers("abc-123-xyz")
        assert result["APIKey"] == "abc-123-xyz"


class TestFlattenCube:
    def test_returns_dataframe(self) -> None:
        response = _cube_response(
            date_labels=["2023"],
            geo_labels=["Bradford"],
            geo_uris=["str:val:db:field:E08000032"],
            values=[[42.0]],
        )
        result = _flatten_cube(response)
        assert isinstance(result, pd.DataFrame)

    def test_row_count_is_product_of_dimensions(self) -> None:
        response = _cube_response(
            date_labels=["2022", "2023"],
            geo_labels=["Bradford", "Leeds"],
            geo_uris=["uri:E08000032", "uri:E08000035"],
            values=[[10.0, 20.0], [30.0, 40.0]],
        )
        result = _flatten_cube(response)
        assert len(result) == 4

    def test_value_column_present(self) -> None:
        response = _cube_response(
            date_labels=["2023"],
            geo_labels=["Bradford"],
            geo_uris=["uri:E08000032"],
            values=[[99.0]],
        )
        result = _flatten_cube(response)
        assert "value" in result.columns

    def test_field_label_columns_present(self) -> None:
        response = _cube_response(
            date_labels=["2023"],
            geo_labels=["Bradford"],
            geo_uris=["uri:E08000032"],
            values=[[99.0]],
        )
        result = _flatten_cube(response)
        assert "Date" in result.columns
        assert "Geography" in result.columns

    def test_uri_columns_present(self) -> None:
        response = _cube_response(
            date_labels=["2023"],
            geo_labels=["Bradford"],
            geo_uris=["uri:E08000032"],
            values=[[99.0]],
        )
        result = _flatten_cube(response)
        assert "Geography_uri" in result.columns

    def test_correct_value_extracted(self) -> None:
        response = _cube_response(
            date_labels=["2023"],
            geo_labels=["Bradford"],
            geo_uris=["uri:E08000032"],
            values=[[123.0]],
        )
        result = _flatten_cube(response)
        assert result["value"].iloc[0] == 123.0

    def test_correct_labels_extracted(self) -> None:
        response = _cube_response(
            date_labels=["2023"],
            geo_labels=["Bradford"],
            geo_uris=["uri:E08000032"],
            values=[[1.0]],
        )
        result = _flatten_cube(response)
        assert result["Date"].iloc[0] == "2023"
        assert result["Geography"].iloc[0] == "Bradford"

    def test_none_value_preserved(self) -> None:
        response = _cube_response(
            date_labels=["2023"],
            geo_labels=["Bradford"],
            geo_uris=["uri:E08000032"],
            values=[[None]],
        )
        result = _flatten_cube(response)
        assert result["value"].iloc[0] is None


class TestPostTable:
    def _mock_response(self, status: int, body: dict) -> MagicMock:
        mock = MagicMock()
        mock.status_code = status
        mock.json.return_value = body
        mock.raise_for_status = MagicMock()
        return mock

    def test_returns_json_on_success(self) -> None:
        expected = {"fields": [], "cubes": {}}
        with patch("requests.post", return_value=self._mock_response(200, expected)):
            result = _post_table({}, "test-key")
        assert result == expected

    def test_401_raises_permission_error(self) -> None:
        mock = self._mock_response(401, {})
        with (
            patch("requests.post", return_value=mock),
            pytest.raises(PermissionError, match="invalid or missing API key"),
        ):
            _post_table({}, "bad-key")

    def test_429_raises_runtime_error(self) -> None:
        mock = self._mock_response(429, {})
        with (
            patch("requests.post", return_value=mock),
            pytest.raises(RuntimeError, match="rate limit"),
        ):
            _post_table({}, "key")

    def test_other_http_error_propagates(self) -> None:
        import requests as req

        mock = self._mock_response(500, {})
        mock.raise_for_status.side_effect = req.HTTPError("500 Server Error")
        with patch("requests.post", return_value=mock), pytest.raises(req.HTTPError):
            _post_table({}, "key")


class TestFetchDateItems:
    def _mock_get(self, children: list[dict], valueset_children: list[dict] | None = None):
        first_response = MagicMock()
        first_response.json.return_value = {"children": children}
        first_response.raise_for_status = MagicMock()

        if valueset_children is not None:
            second_response = MagicMock()
            second_response.json.return_value = {"children": valueset_children}
            second_response.raise_for_status = MagicMock()
            return [first_response, second_response]

        return [first_response]

    def test_returns_ids_from_value_children(self) -> None:
        children = [{"type": "VALUE", "id": "id1"}, {"type": "VALUE", "id": "id2"}]
        responses = self._mock_get(children)
        with patch("requests.get", side_effect=responses):
            result = _fetch_date_items("some:date:field", "api-key")
        assert result == ["id1", "id2"]

    def test_drills_into_valueset_child(self) -> None:
        first_children = [{"type": "VALUESET", "id": "vs:id"}]
        value_children = [{"type": "VALUE", "id": "v1"}, {"type": "VALUE", "id": "v2"}]
        responses = self._mock_get(first_children, value_children)
        with patch("requests.get", side_effect=responses):
            result = _fetch_date_items("some:date:field", "api-key")
        assert result == ["v1", "v2"]


class TestBrowseStatXploreSchema:
    def test_returns_schema_dict(self) -> None:
        expected = {"children": [{"id": "db1", "label": "Dataset 1"}]}
        mock = MagicMock()
        mock.json.return_value = expected
        mock.raise_for_status = MagicMock()
        with patch("requests.get", return_value=mock):
            result = browse_stat_xplore_schema("api-key")
        assert result == expected

    def test_raises_on_http_error(self) -> None:
        import requests as req

        mock = MagicMock()
        mock.raise_for_status.side_effect = req.HTTPError("401")
        with patch("requests.get", return_value=mock), pytest.raises(req.HTTPError):
            browse_stat_xplore_schema("bad-key")


def _yorkshire_cube_response() -> dict:
    yorks_lad = next(iter(YORKSHIRE_LAD_CODES))
    return _cube_response(
        date_labels=["2023-01"],
        geo_labels=["Bradford"],
        geo_uris=[f"str:val:db:field:{yorks_lad}"],
        values=[[1234.0]],
    )


class TestExtractDwpTable:
    def test_returns_dataframe_with_expected_columns(self, test_settings) -> None:
        response = _yorkshire_cube_response()
        with (
            patch("yhovi_pipeline.tasks.extract.dwp._fetch_date_items", return_value=["id1"]),
            patch("yhovi_pipeline.tasks.extract.dwp._post_table", return_value=response),
        ):
            result = _extract_dwp_table(
                database=_CIL_DATABASE,
                measure=_CIL_MEASURE,
                la_valueset=_CIL_LA_VALUESET,
                date_field=_CIL_DATE_FIELD,
                dataset_label="test",
                api_key="key",
            )
        assert set(result.columns) == {"period_label", "lad_name", "lad_code", "value"}

    def test_filters_to_yorkshire_lads(self, test_settings) -> None:
        response = _cube_response(
            date_labels=["2023-01"],
            geo_labels=["London"],
            geo_uris=["str:val:db:field:E09000001"],
            values=[[999.0]],
        )
        with (
            patch("yhovi_pipeline.tasks.extract.dwp._fetch_date_items", return_value=["id1"]),
            patch("yhovi_pipeline.tasks.extract.dwp._post_table", return_value=response),
        ):
            result = _extract_dwp_table(
                database=_CIL_DATABASE,
                measure=_CIL_MEASURE,
                la_valueset=_CIL_LA_VALUESET,
                date_field=_CIL_DATE_FIELD,
                dataset_label="test",
                api_key="key",
            )
        assert len(result) == 0

    def test_respects_recent_periods_limit(self, test_settings) -> None:
        response = _yorkshire_cube_response()
        with (
            patch(
                "yhovi_pipeline.tasks.extract.dwp._fetch_date_items",
                return_value=["id1", "id2", "id3", "id4", "id5"],
            ) as mock_fetch,
            patch("yhovi_pipeline.tasks.extract.dwp._post_table", return_value=response),
        ):
            _extract_dwp_table(
                database=_CIL_DATABASE,
                measure=_CIL_MEASURE,
                la_valueset=_CIL_LA_VALUESET,
                date_field=_CIL_DATE_FIELD,
                dataset_label="test",
                api_key="key",
                recent_periods=2,
            )
        mock_fetch.assert_called_once()


class TestExtractDwpTasks:
    def test_extract_children_low_income_returns_dataframe(self, test_settings) -> None:
        response = _yorkshire_cube_response()
        with (
            patch("yhovi_pipeline.tasks.extract.dwp._fetch_date_items", return_value=["id1"]),
            patch("yhovi_pipeline.tasks.extract.dwp._post_table", return_value=response),
        ):
            result = extract_children_low_income.fn()
        assert isinstance(result, pd.DataFrame)

    def test_extract_pip_claimants_returns_dataframe(self, test_settings) -> None:
        response = _yorkshire_cube_response()
        with (
            patch("yhovi_pipeline.tasks.extract.dwp._fetch_date_items", return_value=["id1"]),
            patch("yhovi_pipeline.tasks.extract.dwp._post_table", return_value=response),
        ):
            result = extract_pip_claimants.fn()
        assert isinstance(result, pd.DataFrame)
