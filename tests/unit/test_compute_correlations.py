"""Unit tests for yhovi_pipeline.utils.compute_correlations."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd

from yhovi_pipeline.utils.compute_correlations import (
    _generate_message,
    compute_and_store_correlations,
)


def _mock_engine() -> MagicMock:
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)
    engine.begin.return_value.__enter__ = MagicMock(return_value=conn)
    engine.begin.return_value.__exit__ = MagicMock(return_value=False)
    return engine


_CORR_DF = pd.DataFrame(
    {
        "indicator_id": ["employment_rate"] * 3 + ["unemployment_rate"] * 3,
        "indicator_name": ["Employment Rate"] * 3 + ["Unemployment Rate"] * 3,
        "lad_code": ["E08000032", "E08000033", "E08000034"] * 2,
        "year": [2020] * 6,
        "value": [75.0, 76.0, 77.0, 5.0, 4.0, 3.0],
    }
)


class TestGenerateMessage:
    def test_no_meaningful_not_significant(self) -> None:
        msg = _generate_message(0.05, 0.50)
        assert "no meaningful relationship" in msg
        assert "not statistically significant" in msg

    def test_no_meaningful_but_significant(self) -> None:
        msg = _generate_message(0.05, 0.01)
        assert "very weak" in msg
        assert "statistically significant" in msg

    def test_weak_positive_significant(self) -> None:
        msg = _generate_message(0.3, 0.01)
        assert "weak" in msg
        assert "positive" in msg
        assert "statistically significant" in msg

    def test_weak_negative_not_significant(self) -> None:
        msg = _generate_message(-0.3, 0.50)
        assert "weak" in msg
        assert "negative" in msg
        assert "not statistically significant" in msg

    def test_moderate_positive_not_significant(self) -> None:
        msg = _generate_message(0.5, 0.10)
        assert "moderate" in msg
        assert "positive" in msg
        assert "not statistically significant" in msg

    def test_strong_negative_significant(self) -> None:
        msg = _generate_message(-0.7, 0.01)
        assert "strong" in msg
        assert "negative" in msg
        assert "statistically significant" in msg

    def test_very_strong_positive_significant(self) -> None:
        msg = _generate_message(0.9, 0.001)
        assert "very strong" in msg
        assert "positive" in msg
        assert "statistically significant" in msg


class TestComputeAndStoreCorrelations:
    def test_returns_pair_count(self, test_settings) -> None:
        engine = _mock_engine()
        with (
            patch("yhovi_pipeline.utils.compute_correlations.create_engine", return_value=engine),
            patch("pandas.read_sql", return_value=_CORR_DF),
        ):
            result = compute_and_store_correlations()
        assert result == 4  # 2 indicators x 2

    def test_returns_zero_for_empty_indicator_table(self, test_settings) -> None:
        engine = _mock_engine()
        empty_df = pd.DataFrame(
            columns=["indicator_id", "indicator_name", "lad_code", "year", "value"]
        )
        with (
            patch("yhovi_pipeline.utils.compute_correlations.create_engine", return_value=engine),
            patch("pandas.read_sql", return_value=empty_df),
        ):
            result = compute_and_store_correlations()
        assert result == 0
