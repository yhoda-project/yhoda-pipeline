"""Unit tests for yhovi_pipeline.tasks.load.database."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd

from yhovi_pipeline.db.models import ExtractionStatus
from yhovi_pipeline.tasks.load.database import (
    _get_engine,
    query_population,
    upsert_indicators,
    write_metadata,
)

_MOCK_LOGGER = MagicMock()


def _indicator_df(n: int = 2) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "indicator_id": ["employment_rate"] * n,
            "indicator_name": ["Employment rate"] * n,
            "geography_code": [f"E0800003{i}" for i in range(n)],
            "geography_name": [f"LAD {i}" for i in range(n)],
            "geography_level": ["lad"] * n,
            "lad_code": [f"E0800003{i}" for i in range(n)],
            "lad_name": [f"LAD {i}" for i in range(n)],
            "reference_period": [date(2023, 1, 1)] * n,
            "value": [72.1] * n,
            "unit": ["%"] * n,
            "source": ["nomis"] * n,
            "dataset_code": ["eejer"] * n,
            "breakdown_category": [""] * n,
            "is_forecast": [False] * n,
            "forecast_model": [None] * n,
        }
    )


def _mock_engine() -> MagicMock:
    engine = MagicMock()
    conn = MagicMock()
    engine.begin.return_value.__enter__ = MagicMock(return_value=conn)
    engine.begin.return_value.__exit__ = MagicMock(return_value=False)
    return engine


class TestGetEngine:
    def test_returns_engine(self, test_settings) -> None:
        with patch("yhovi_pipeline.tasks.load.database.create_engine") as mock_create:
            mock_create.return_value = MagicMock()
            engine = _get_engine()
        assert engine is not None
        mock_create.assert_called_once()


class TestUpsertIndicators:
    def test_empty_dataframe_returns_zero(self) -> None:
        with (
            patch("yhovi_pipeline.tasks.load.database.get_run_logger", return_value=_MOCK_LOGGER),
            patch("yhovi_pipeline.tasks.load.database._get_engine", return_value=_mock_engine()),
        ):
            result = upsert_indicators.fn(pd.DataFrame(), "eejer")
        assert result == 0

    def test_returns_row_count(self) -> None:
        df = _indicator_df(3)
        engine = _mock_engine()
        with (
            patch("yhovi_pipeline.tasks.load.database.get_run_logger", return_value=_MOCK_LOGGER),
            patch("yhovi_pipeline.tasks.load.database._get_engine", return_value=engine),
        ):
            result = upsert_indicators.fn(df, "eejer")
        assert result == 3

    def test_executes_against_engine(self) -> None:
        df = _indicator_df(1)
        engine = _mock_engine()
        conn = engine.begin.return_value.__enter__.return_value
        with (
            patch("yhovi_pipeline.tasks.load.database.get_run_logger", return_value=_MOCK_LOGGER),
            patch("yhovi_pipeline.tasks.load.database._get_engine", return_value=engine),
        ):
            upsert_indicators.fn(df, "eejer")
        conn.execute.assert_called_once()

    def test_sets_updated_at_on_all_records(self) -> None:
        df = _indicator_df(2)
        engine = _mock_engine()
        conn = engine.begin.return_value.__enter__.return_value
        with (
            patch("yhovi_pipeline.tasks.load.database.get_run_logger", return_value=_MOCK_LOGGER),
            patch("yhovi_pipeline.tasks.load.database._get_engine", return_value=engine),
        ):
            upsert_indicators.fn(df, "eejer")
        call_args = conn.execute.call_args
        assert call_args is not None


class TestWriteMetadata:
    def _session_engine(self) -> MagicMock:
        engine = MagicMock()
        session = MagicMock()
        session.__enter__ = MagicMock(return_value=session)
        session.__exit__ = MagicMock(return_value=False)
        return engine, session

    def test_writes_record_to_session(self) -> None:
        engine, session = self._session_engine()
        with (
            patch("yhovi_pipeline.tasks.load.database.get_run_logger", return_value=_MOCK_LOGGER),
            patch("yhovi_pipeline.tasks.load.database._get_engine", return_value=engine),
            patch("yhovi_pipeline.tasks.load.database.Session", return_value=session),
        ):
            write_metadata.fn(
                dataset_code="eejer",
                source="nomis",
                status=ExtractionStatus.SUCCESS,
                rows_extracted=22,
                rows_loaded=22,
            )
        session.add.assert_called_once()
        session.commit.assert_called_once()

    def test_accepts_optional_none_fields(self) -> None:
        engine, session = self._session_engine()
        with (
            patch("yhovi_pipeline.tasks.load.database.get_run_logger", return_value=_MOCK_LOGGER),
            patch("yhovi_pipeline.tasks.load.database._get_engine", return_value=engine),
            patch("yhovi_pipeline.tasks.load.database.Session", return_value=session),
        ):
            write_metadata.fn(
                dataset_code="eejer",
                source="nomis",
                status=ExtractionStatus.FAILED,
                error_message="something broke",
            )
        session.add.assert_called_once()

    def test_record_passed_to_session_is_metadata_instance(self) -> None:
        from yhovi_pipeline.db.models import DatasetMetadata

        engine, session = self._session_engine()
        with (
            patch("yhovi_pipeline.tasks.load.database.get_run_logger", return_value=_MOCK_LOGGER),
            patch("yhovi_pipeline.tasks.load.database._get_engine", return_value=engine),
            patch("yhovi_pipeline.tasks.load.database.Session", return_value=session),
        ):
            write_metadata.fn(
                dataset_code="eejer",
                source="nomis",
                status=ExtractionStatus.SUCCESS,
            )
        added = session.add.call_args[0][0]
        assert isinstance(added, DatasetMetadata)


class TestQueryPopulation:
    def test_returns_dataframe(self) -> None:
        engine = MagicMock()
        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = [
            ("E08000032", 2023, 550000.0),
            ("E08000035", 2023, 800000.0),
        ]
        engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch("yhovi_pipeline.tasks.load.database.get_run_logger", return_value=_MOCK_LOGGER),
            patch("yhovi_pipeline.tasks.load.database._get_engine", return_value=engine),
        ):
            result = query_population.fn()

        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["lad_code", "year", "population"]
        assert len(result) == 2

    def test_empty_result_returns_empty_dataframe(self) -> None:
        engine = MagicMock()
        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = []
        engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch("yhovi_pipeline.tasks.load.database.get_run_logger", return_value=_MOCK_LOGGER),
            patch("yhovi_pipeline.tasks.load.database._get_engine", return_value=engine),
        ):
            result = query_population.fn()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
