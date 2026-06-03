"""Unit tests for the five active ETL flows and the master orchestrator.

All external dependencies (tasks, DB, SMTP) are mocked so tests run
without a real database or API key.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from yhovi_pipeline.flows.economy.claimant_count import (
    claimant_count_flow,
)
from yhovi_pipeline.flows.economy.earnings import (
    ASHE_COLUMNS,
    DATASET_CODE,
    earnings_flow,
)
from yhovi_pipeline.flows.economy.employment_jobs import (
    APS_DATASETS,
    NOMIS_ANNUAL_COLUMNS,
    NOMIS_APS_COLUMNS,
    employment_jobs_flow,
)
from yhovi_pipeline.flows.orchestrator import full_refresh_flow
from yhovi_pipeline.flows.society.education_attainment import (
    QUALIFICATION_DATASETS,
    education_attainment_flow,
)
from yhovi_pipeline.flows.society.health_outcomes import (
    HEALTH_DATASETS,
    health_outcomes_flow,
)

_SAMPLE_DF = pd.DataFrame({"col": [1]})
_INDICATOR_DF = pd.DataFrame({"indicator_id": ["test"], "value": [1.0]})


# ---------------------------------------------------------------------------
# Earnings flow
# ---------------------------------------------------------------------------


class TestEarningsFlow:
    _mod = "yhovi_pipeline.flows.economy.earnings"

    def test_success_path_runs_without_error(self) -> None:
        with (
            patch(f"{self._mod}.extract_ashe", return_value=_SAMPLE_DF),
            patch(f"{self._mod}.validate_schema", return_value=_SAMPLE_DF),
            patch(f"{self._mod}.normalise_nomis_ashe", return_value=_INDICATOR_DF),
            patch(f"{self._mod}.upsert_indicators", return_value=1),
            patch(f"{self._mod}.write_metadata"),
            patch(f"{self._mod}.create_table_artifact"),
        ):
            earnings_flow.fn()

    def test_artifact_created_on_success(self) -> None:
        with (
            patch(f"{self._mod}.extract_ashe", return_value=_SAMPLE_DF),
            patch(f"{self._mod}.validate_schema", return_value=_SAMPLE_DF),
            patch(f"{self._mod}.normalise_nomis_ashe", return_value=_INDICATOR_DF),
            patch(f"{self._mod}.upsert_indicators", return_value=1),
            patch(f"{self._mod}.write_metadata"),
            patch(f"{self._mod}.create_table_artifact") as mock_artifact,
        ):
            earnings_flow.fn()
        mock_artifact.assert_called_once()

    def test_failure_reraises_exception(self) -> None:
        with (
            patch(f"{self._mod}.extract_ashe", side_effect=RuntimeError("API down")),
            patch(f"{self._mod}.write_metadata"),
            patch(f"{self._mod}.send_failure_alert"),
            patch(f"{self._mod}.create_table_artifact"),
            pytest.raises(RuntimeError, match="API down"),
        ):
            earnings_flow.fn()

    def test_failure_calls_write_metadata(self) -> None:
        with (
            patch(f"{self._mod}.extract_ashe", side_effect=RuntimeError("fail")),
            patch(f"{self._mod}.write_metadata") as mock_meta,
            patch(f"{self._mod}.send_failure_alert"),
            patch(f"{self._mod}.create_table_artifact"),
            pytest.raises(RuntimeError),
        ):
            earnings_flow.fn()
        mock_meta.assert_called_once()

    def test_failure_sends_alert(self) -> None:
        with (
            patch(f"{self._mod}.extract_ashe", side_effect=RuntimeError("fail")),
            patch(f"{self._mod}.write_metadata"),
            patch(f"{self._mod}.send_failure_alert") as mock_alert,
            patch(f"{self._mod}.create_table_artifact"),
            pytest.raises(RuntimeError),
        ):
            earnings_flow.fn()
        mock_alert.assert_called_once()

    def test_dataset_code_constant(self) -> None:
        assert DATASET_CODE == "eejpay"

    def test_ashe_columns_constant_contains_expected_fields(self) -> None:
        assert "DATE_NAME" in ASHE_COLUMNS
        assert "OBS_VALUE" in ASHE_COLUMNS
        assert "GEOGRAPHY_CODE" in ASHE_COLUMNS


# ---------------------------------------------------------------------------
# Employment & Jobs flow
# ---------------------------------------------------------------------------


class TestEmploymentJobsFlow:
    _mod = "yhovi_pipeline.flows.economy.employment_jobs"

    def test_success_path_runs_without_error(self) -> None:
        with (
            patch(f"{self._mod}.extract_aps", return_value=_SAMPLE_DF),
            patch(f"{self._mod}.extract_jobs_density", return_value=_SAMPLE_DF),
            patch(f"{self._mod}.validate_schema", return_value=_SAMPLE_DF),
            patch(f"{self._mod}.normalise_nomis_aps", return_value=_INDICATOR_DF),
            patch(f"{self._mod}.normalise_nomis_annual", return_value=_INDICATOR_DF),
            patch(f"{self._mod}.upsert_indicators", return_value=1),
            patch(f"{self._mod}.write_metadata"),
            patch(f"{self._mod}.create_table_artifact"),
        ):
            employment_jobs_flow.fn()

    def test_aps_failure_reraises(self) -> None:
        with (
            patch(f"{self._mod}.extract_aps", side_effect=RuntimeError("aps fail")),
            patch(f"{self._mod}.write_metadata"),
            patch(f"{self._mod}.send_failure_alert"),
            patch(f"{self._mod}.create_table_artifact"),
            pytest.raises(RuntimeError, match="aps fail"),
        ):
            employment_jobs_flow.fn()

    def test_jobs_density_failure_reraises(self) -> None:
        with (
            patch(f"{self._mod}.extract_aps", return_value=_SAMPLE_DF),
            patch(f"{self._mod}.extract_jobs_density", side_effect=RuntimeError("density fail")),
            patch(f"{self._mod}.validate_schema", return_value=_SAMPLE_DF),
            patch(f"{self._mod}.normalise_nomis_aps", return_value=_INDICATOR_DF),
            patch(f"{self._mod}.upsert_indicators", return_value=1),
            patch(f"{self._mod}.write_metadata"),
            patch(f"{self._mod}.send_failure_alert"),
            patch(f"{self._mod}.create_table_artifact"),
            pytest.raises(RuntimeError, match="density fail"),
        ):
            employment_jobs_flow.fn()

    def test_aps_datasets_has_four_entries(self) -> None:
        assert len(APS_DATASETS) == 4

    def test_aps_columns_constant_correct(self) -> None:
        assert "VARIABLE_NAME" in NOMIS_APS_COLUMNS
        assert "OBS_VALUE" in NOMIS_APS_COLUMNS

    def test_annual_columns_constant_correct(self) -> None:
        assert "OBS_VALUE" in NOMIS_ANNUAL_COLUMNS
        assert "DATE_NAME" in NOMIS_ANNUAL_COLUMNS


# ---------------------------------------------------------------------------
# Health Outcomes flow
# ---------------------------------------------------------------------------


class TestHealthOutcomesFlow:
    _mod = "yhovi_pipeline.flows.society.health_outcomes"

    def test_success_path_runs_without_error(self) -> None:
        with (
            patch(f"{self._mod}.extract_fingertips_indicators", return_value=_SAMPLE_DF),
            patch(f"{self._mod}.validate_schema", return_value=_SAMPLE_DF),
            patch(f"{self._mod}.normalise_fingertips", return_value=_INDICATOR_DF),
            patch(f"{self._mod}.upsert_indicators", return_value=1),
            patch(f"{self._mod}.write_metadata"),
            patch(f"{self._mod}.create_table_artifact"),
        ):
            health_outcomes_flow.fn()

    def test_failure_reraises(self) -> None:
        with (
            patch(
                f"{self._mod}.extract_fingertips_indicators",
                side_effect=RuntimeError("fingertips down"),
            ),
            patch(f"{self._mod}.write_metadata"),
            patch(f"{self._mod}.send_failure_alert"),
            patch(f"{self._mod}.create_table_artifact"),
            pytest.raises(RuntimeError, match="fingertips down"),
        ):
            health_outcomes_flow.fn()

    def test_failure_calls_write_metadata_with_failed_status(self) -> None:
        from yhovi_pipeline.db.models import ExtractionStatus

        with (
            patch(
                f"{self._mod}.extract_fingertips_indicators",
                side_effect=RuntimeError("fail"),
            ),
            patch(f"{self._mod}.write_metadata") as mock_meta,
            patch(f"{self._mod}.send_failure_alert"),
            patch(f"{self._mod}.create_table_artifact"),
            pytest.raises(RuntimeError),
        ):
            health_outcomes_flow.fn()
        call_kwargs = mock_meta.call_args.kwargs
        assert call_kwargs["status"] == ExtractionStatus.FAILED

    def test_health_datasets_has_five_entries(self) -> None:
        assert len(HEALTH_DATASETS) == 5

    def test_health_datasets_all_have_required_keys(self) -> None:
        for code, meta in HEALTH_DATASETS.items():
            assert "fingertips_id" in meta, f"{code} missing fingertips_id"
            assert "indicator_id" in meta, f"{code} missing indicator_id"
            assert "gender_filter" in meta, f"{code} missing gender_filter"
            assert "age_filter" in meta, f"{code} missing age_filter"


# ---------------------------------------------------------------------------
# Education Attainment flow
# ---------------------------------------------------------------------------


class TestEducationAttainmentFlow:
    _mod = "yhovi_pipeline.flows.society.education_attainment"

    def test_success_path_runs_without_error(self) -> None:
        with (
            patch(f"{self._mod}.extract_aps", return_value=_SAMPLE_DF),
            patch(f"{self._mod}.validate_schema", return_value=_SAMPLE_DF),
            patch(f"{self._mod}.normalise_nomis_aps", return_value=_INDICATOR_DF),
            patch(f"{self._mod}.upsert_indicators", return_value=1),
            patch(f"{self._mod}.write_metadata"),
            patch(f"{self._mod}.create_table_artifact"),
        ):
            education_attainment_flow.fn()

    def test_failure_reraises(self) -> None:
        with (
            patch(f"{self._mod}.extract_aps", side_effect=RuntimeError("aps fail")),
            patch(f"{self._mod}.write_metadata"),
            patch(f"{self._mod}.send_failure_alert"),
            patch(f"{self._mod}.create_table_artifact"),
            pytest.raises(RuntimeError, match="aps fail"),
        ):
            education_attainment_flow.fn()

    def test_qualification_datasets_has_two_entries(self) -> None:
        assert len(QUALIFICATION_DATASETS) == 2

    def test_each_qualification_dataset_has_required_keys(self) -> None:
        for key, meta in QUALIFICATION_DATASETS.items():
            assert "indicator_id" in meta, f"{key} missing indicator_id"
            assert "dataset_code" in meta, f"{key} missing dataset_code"
            assert "unit" in meta, f"{key} missing unit"


# ---------------------------------------------------------------------------
# Claimant Count flow
# ---------------------------------------------------------------------------


def _mock_dataset_config(extract_return=None) -> MagicMock:
    """Return a mock _DatasetConfig with controlled extract_fn."""
    ds = MagicMock()
    ds.extract_fn.return_value = extract_return if extract_return is not None else _SAMPLE_DF
    ds.dataset_code = "test_code"
    ds.indicator_id = "test_id"
    ds.indicator_name = "Test Indicator"
    ds.rate_per = 10_000
    ds.unit = "per 10k"
    return ds


class TestClaimantCountFlow:
    _mod = "yhovi_pipeline.flows.economy.claimant_count"

    def test_success_path_runs_without_error(self) -> None:
        ds = _mock_dataset_config()
        with (
            patch(f"{self._mod}._DATASETS", [ds]),
            patch(f"{self._mod}.query_population", return_value=_SAMPLE_DF),
            patch(f"{self._mod}.normalise_dwp", return_value=_INDICATOR_DF),
            patch(f"{self._mod}.upsert_indicators", return_value=1),
            patch(f"{self._mod}.write_metadata"),
            patch(f"{self._mod}.create_table_artifact"),
            patch(f"{self._mod}.send_failure_alert"),
        ):
            claimant_count_flow.fn()

    def test_failure_accumulates_and_raises_runtime_error(self) -> None:
        ds = _mock_dataset_config()
        ds.extract_fn.side_effect = RuntimeError("DWP down")
        with (
            patch(f"{self._mod}._DATASETS", [ds]),
            patch(f"{self._mod}.query_population", return_value=_SAMPLE_DF),
            patch(f"{self._mod}.normalise_dwp", return_value=_INDICATOR_DF),
            patch(f"{self._mod}.upsert_indicators", return_value=0),
            patch(f"{self._mod}.write_metadata"),
            patch(f"{self._mod}.create_table_artifact"),
            patch(f"{self._mod}.send_failure_alert"),
            pytest.raises(RuntimeError),
        ):
            claimant_count_flow.fn()

    def test_failure_sends_single_consolidated_alert(self) -> None:
        ds1 = _mock_dataset_config()
        ds1.extract_fn.side_effect = RuntimeError("fail1")
        ds2 = _mock_dataset_config()
        ds2.dataset_code = "code2"
        ds2.extract_fn.side_effect = RuntimeError("fail2")
        with (
            patch(f"{self._mod}._DATASETS", [ds1, ds2]),
            patch(f"{self._mod}.query_population", return_value=_SAMPLE_DF),
            patch(f"{self._mod}.normalise_dwp", return_value=_INDICATOR_DF),
            patch(f"{self._mod}.upsert_indicators", return_value=0),
            patch(f"{self._mod}.write_metadata"),
            patch(f"{self._mod}.create_table_artifact"),
            patch(f"{self._mod}.send_failure_alert") as mock_alert,
            pytest.raises(RuntimeError),
        ):
            claimant_count_flow.fn()
        mock_alert.assert_called_once()

    def test_no_failure_alert_on_success(self) -> None:
        ds = _mock_dataset_config()
        with (
            patch(f"{self._mod}._DATASETS", [ds]),
            patch(f"{self._mod}.query_population", return_value=_SAMPLE_DF),
            patch(f"{self._mod}.normalise_dwp", return_value=_INDICATOR_DF),
            patch(f"{self._mod}.upsert_indicators", return_value=1),
            patch(f"{self._mod}.write_metadata"),
            patch(f"{self._mod}.create_table_artifact"),
            patch(f"{self._mod}.send_failure_alert") as mock_alert,
        ):
            claimant_count_flow.fn()
        mock_alert.assert_not_called()


# ---------------------------------------------------------------------------
# Orchestrator flow
# ---------------------------------------------------------------------------


class TestFullRefreshFlow:
    _mod = "yhovi_pipeline.flows.orchestrator"

    def _all_flow_patches(self) -> list:
        names = [
            "employment_jobs_flow",
            "earnings_flow",
            "claimant_count_flow",
            "business_demography_flow",
            "gdp_gva_flow",
            "health_outcomes_flow",
            "education_attainment_flow",
            "housing_tenure_flow",
            "deprivation_imd_flow",
            "crime_statistics_flow",
            "physical_activity_flow",
            "digital_inclusion_flow",
            "air_quality_flow",
            "energy_consumption_flow",
        ]
        return [patch(f"{self._mod}.{name}") for name in names]

    def test_all_fourteen_flows_called(self) -> None:
        patches = self._all_flow_patches()
        mocks = [p.start() for p in patches]
        try:
            with (
                patch(f"{self._mod}.get_run_logger", return_value=MagicMock()),
                patch(f"{self._mod}.create_markdown_artifact"),
            ):
                full_refresh_flow.fn()
        finally:
            for p in patches:
                p.stop()
        for mock in mocks:
            mock.assert_called_once()

    def test_completes_without_error(self) -> None:
        patches = self._all_flow_patches()
        for p in patches:
            p.start()
        try:
            with (
                patch(f"{self._mod}.get_run_logger", return_value=MagicMock()),
                patch(f"{self._mod}.create_markdown_artifact"),
            ):
                full_refresh_flow.fn()
        finally:
            for p in patches:
                p.stop()

    def test_markdown_artifact_created(self) -> None:
        patches = self._all_flow_patches()
        for p in patches:
            p.start()
        try:
            with (
                patch(f"{self._mod}.get_run_logger", return_value=MagicMock()),
                patch(f"{self._mod}.create_markdown_artifact") as mock_artifact,
            ):
                full_refresh_flow.fn()
        finally:
            for p in patches:
                p.stop()
        mock_artifact.assert_called_once()
