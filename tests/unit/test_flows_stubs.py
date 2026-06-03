"""Unit tests for the nine static-release stub flows.

Each stub flow logs a message and creates a markdown artifact — no tasks
are run.  Tests verify the flows execute without error and call
``create_markdown_artifact`` exactly once.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from yhovi_pipeline.flows.economy.business_demography import business_demography_flow
from yhovi_pipeline.flows.economy.gdp_gva import gdp_gva_flow
from yhovi_pipeline.flows.environment.air_quality import air_quality_flow
from yhovi_pipeline.flows.environment.energy_consumption import energy_consumption_flow
from yhovi_pipeline.flows.society.crime_statistics import crime_statistics_flow
from yhovi_pipeline.flows.society.deprivation_imd import deprivation_imd_flow
from yhovi_pipeline.flows.society.digital_inclusion import digital_inclusion_flow
from yhovi_pipeline.flows.society.housing_tenure import housing_tenure_flow
from yhovi_pipeline.flows.society.physical_activity import physical_activity_flow


def _run_stub(module_path: str, flow_fn) -> MagicMock:
    """Call a stub flow with mocked Prefect dependencies; return the artifact mock."""
    mock_artifact = MagicMock()
    with (
        patch(f"{module_path}.get_run_logger", return_value=MagicMock()),
        patch(f"{module_path}.create_markdown_artifact", mock_artifact),
    ):
        flow_fn.fn()
    return mock_artifact


class TestBusinessDemographyFlow:
    _mod = "yhovi_pipeline.flows.economy.business_demography"

    def test_completes_without_error(self) -> None:
        _run_stub(self._mod, business_demography_flow)

    def test_creates_markdown_artifact(self) -> None:
        mock_artifact = _run_stub(self._mod, business_demography_flow)
        mock_artifact.assert_called_once()


class TestGdpGvaFlow:
    _mod = "yhovi_pipeline.flows.economy.gdp_gva"

    def test_completes_without_error(self) -> None:
        _run_stub(self._mod, gdp_gva_flow)

    def test_creates_markdown_artifact(self) -> None:
        mock_artifact = _run_stub(self._mod, gdp_gva_flow)
        mock_artifact.assert_called_once()


class TestAirQualityFlow:
    _mod = "yhovi_pipeline.flows.environment.air_quality"

    def test_completes_without_error(self) -> None:
        _run_stub(self._mod, air_quality_flow)

    def test_creates_markdown_artifact(self) -> None:
        mock_artifact = _run_stub(self._mod, air_quality_flow)
        mock_artifact.assert_called_once()


class TestEnergyConsumptionFlow:
    _mod = "yhovi_pipeline.flows.environment.energy_consumption"

    def test_completes_without_error(self) -> None:
        _run_stub(self._mod, energy_consumption_flow)

    def test_creates_markdown_artifact(self) -> None:
        mock_artifact = _run_stub(self._mod, energy_consumption_flow)
        mock_artifact.assert_called_once()


class TestCrimeStatisticsFlow:
    _mod = "yhovi_pipeline.flows.society.crime_statistics"

    def test_completes_without_error(self) -> None:
        _run_stub(self._mod, crime_statistics_flow)

    def test_creates_markdown_artifact(self) -> None:
        mock_artifact = _run_stub(self._mod, crime_statistics_flow)
        mock_artifact.assert_called_once()


class TestDeprivationImdFlow:
    _mod = "yhovi_pipeline.flows.society.deprivation_imd"

    def test_completes_without_error(self) -> None:
        _run_stub(self._mod, deprivation_imd_flow)

    def test_creates_markdown_artifact(self) -> None:
        mock_artifact = _run_stub(self._mod, deprivation_imd_flow)
        mock_artifact.assert_called_once()


class TestDigitalInclusionFlow:
    _mod = "yhovi_pipeline.flows.society.digital_inclusion"

    def test_completes_without_error(self) -> None:
        _run_stub(self._mod, digital_inclusion_flow)

    def test_creates_markdown_artifact(self) -> None:
        mock_artifact = _run_stub(self._mod, digital_inclusion_flow)
        mock_artifact.assert_called_once()


class TestHousingTenureFlow:
    _mod = "yhovi_pipeline.flows.society.housing_tenure"

    def test_completes_without_error(self) -> None:
        _run_stub(self._mod, housing_tenure_flow)

    def test_creates_markdown_artifact(self) -> None:
        mock_artifact = _run_stub(self._mod, housing_tenure_flow)
        mock_artifact.assert_called_once()


class TestPhysicalActivityFlow:
    _mod = "yhovi_pipeline.flows.society.physical_activity"

    def test_completes_without_error(self) -> None:
        _run_stub(self._mod, physical_activity_flow)

    def test_creates_markdown_artifact(self) -> None:
        mock_artifact = _run_stub(self._mod, physical_activity_flow)
        mock_artifact.assert_called_once()
