"""Tests that unimplemented stub tasks raise NotImplementedError.

Ensures stubs are not accidentally called in production and documents
which tasks are pending implementation.
"""

from __future__ import annotations

import pandas as pd
import pytest

from yhovi_pipeline.db.models import ExtractionStatus
from yhovi_pipeline.tasks.extract.beis import extract_energy_consumption
from yhovi_pipeline.tasks.extract.defra import extract_aurn
from yhovi_pipeline.tasks.extract.ofcom import extract_connected_nations
from yhovi_pipeline.tasks.extract.ons import (
    extract_business_demography,
    extract_housing_tenure,
    extract_regional_accounts,
)
from yhovi_pipeline.tasks.extract.sport_england import extract_active_lives
from yhovi_pipeline.tasks.transform.geo import aggregate_to_lad
from yhovi_pipeline.utils.metadata import build_metadata_record


class TestUnimplementedStubs:
    def test_extract_energy_consumption_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            extract_energy_consumption.fn(reference_year=2023)

    def test_extract_aurn_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            extract_aurn.fn(reference_year=2023)

    def test_extract_connected_nations_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            extract_connected_nations.fn(reference_year=2023)

    def test_extract_active_lives_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            extract_active_lives.fn(survey_year="2023-24")

    def test_extract_regional_accounts_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            extract_regional_accounts.fn(reference_year=2023)

    def test_extract_business_demography_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            extract_business_demography.fn(reference_year=2023)

    def test_extract_housing_tenure_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            extract_housing_tenure.fn(reference_year=2023)

    def test_aggregate_to_lad_not_implemented(self) -> None:
        df = pd.DataFrame({"lsoa_code": ["E01000001"], "value": [1.0]})
        with pytest.raises(NotImplementedError):
            aggregate_to_lad.fn(df, value_col="value")

    def test_build_metadata_record_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            build_metadata_record("dataset", "source", ExtractionStatus.PENDING)
