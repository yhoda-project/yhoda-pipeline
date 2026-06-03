"""Unit tests for yhovi_pipeline.tasks.transform.validate."""

from __future__ import annotations

import pandas as pd
import pytest

from yhovi_pipeline.config import YORKSHIRE_LAD_CODES
from yhovi_pipeline.tasks.transform.validate import validate_schema, validate_yorkshire_lads


class TestValidateSchema:
    def test_returns_df_unchanged_when_valid(self) -> None:
        df = pd.DataFrame({"col_a": [1, 2], "col_b": [3, 4]})
        result = validate_schema.fn(df, ["col_a", "col_b"], "test-source")
        pd.testing.assert_frame_equal(result, df)

    def test_raises_on_empty_dataframe(self) -> None:
        df = pd.DataFrame({"col_a": []})
        with pytest.raises(ValueError, match="Empty DataFrame"):
            validate_schema.fn(df, ["col_a"], "test-source")

    def test_raises_on_missing_columns(self) -> None:
        df = pd.DataFrame({"col_a": [1]})
        with pytest.raises(ValueError, match="Missing columns"):
            validate_schema.fn(df, ["col_a", "col_b"], "test-source")

    def test_error_message_includes_source_name(self) -> None:
        df = pd.DataFrame({"col_a": []})
        with pytest.raises(ValueError, match="my-source"):
            validate_schema.fn(df, ["col_a"], "my-source")

    def test_partial_column_match_raises(self) -> None:
        df = pd.DataFrame({"col_a": [1], "col_c": [2]})
        with pytest.raises(ValueError, match="col_b"):
            validate_schema.fn(df, ["col_a", "col_b"], "source")

    def test_extra_columns_are_allowed(self) -> None:
        df = pd.DataFrame({"col_a": [1], "col_b": [2], "col_extra": [3]})
        result = validate_schema.fn(df, ["col_a", "col_b"], "source")
        assert "col_extra" in result.columns

    def test_empty_required_columns_passes(self) -> None:
        df = pd.DataFrame({"col_a": [1]})
        result = validate_schema.fn(df, [], "source")
        pd.testing.assert_frame_equal(result, df)


class TestValidateYorkshireLads:
    def _full_yorkshire_df(self) -> pd.DataFrame:
        return pd.DataFrame({"lad_code": list(YORKSHIRE_LAD_CODES)})

    def test_returns_df_unchanged_when_all_lads_present(self) -> None:
        df = self._full_yorkshire_df()
        result = validate_yorkshire_lads.fn(df)
        pd.testing.assert_frame_equal(result, df)

    def test_missing_lads_does_not_raise(self) -> None:
        df = pd.DataFrame({"lad_code": ["E06000061"]})
        validate_yorkshire_lads.fn(df)

    def test_missing_lads_still_returns_df(self) -> None:
        df = pd.DataFrame({"lad_code": ["E06000061"]})
        result = validate_yorkshire_lads.fn(df)
        pd.testing.assert_frame_equal(result, df)

    def test_custom_lad_col(self) -> None:
        df = pd.DataFrame({"area_code": list(YORKSHIRE_LAD_CODES)})
        result = validate_yorkshire_lads.fn(df, lad_col="area_code")
        pd.testing.assert_frame_equal(result, df)

    def test_empty_df_missing_lads_does_not_raise(self) -> None:
        df = pd.DataFrame({"lad_code": []})
        validate_yorkshire_lads.fn(df)
