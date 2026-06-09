"""Unit tests for yhovi_pipeline.tasks.transform.geo."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from yhovi_pipeline.tasks.transform.geo import aggregate_to_lad

_GEO_LOOKUP = pd.DataFrame(
    {
        "lsoa_code": ["E01000001", "E01000002"],
        "msoa_code": ["E02000001", "E02000001"],
        "lad_code": ["E08000032", "E08000032"],
        "lad_name": ["Bradford", "Bradford"],
    }
)


class TestAggregateToLad:
    def test_aggregates_lsoa_to_lad_mean(self) -> None:
        df = pd.DataFrame({"lsoa_code": ["E01000001", "E01000002"], "score": [10.0, 20.0]})
        with patch("yhovi_pipeline.tasks.transform.geo.get_geo_lookup", return_value=_GEO_LOOKUP):
            result = aggregate_to_lad.fn(df, value_col="score")
        assert len(result) == 1
        assert result["lad_code"].iloc[0] == "E08000032"
        assert result["value"].iloc[0] == 15.0

    def test_aggregates_msoa_to_lad(self) -> None:
        geo = _GEO_LOOKUP.drop_duplicates("msoa_code").copy()
        df = pd.DataFrame({"msoa_code": ["E02000001"], "score": [15.0]})
        with patch("yhovi_pipeline.tasks.transform.geo.get_geo_lookup", return_value=geo):
            result = aggregate_to_lad.fn(df, value_col="score", geo_col="msoa_code")
        assert len(result) == 1
        assert result["lad_code"].iloc[0] == "E08000032"

    def test_raises_for_unsupported_geo_col(self) -> None:
        df = pd.DataFrame({"oa_code": ["E00000001"], "score": [5.0]})
        with (
            patch("yhovi_pipeline.tasks.transform.geo.get_geo_lookup", return_value=_GEO_LOOKUP),
            pytest.raises(ValueError, match="Unsupported geo_col"),
        ):
            aggregate_to_lad.fn(df, value_col="score", geo_col="oa_code")
