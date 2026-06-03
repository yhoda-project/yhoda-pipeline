"""Unit tests for yhovi_pipeline.db.models."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from yhovi_pipeline.db.models import (
    DatasetMetadata,
    ExtractionStatus,
    GeoLookup,
    Indicator,
    IndustryBusiness,
    IndustryBusinessKpi,
    JobsLsoa,
)


class TestExtractionStatus:
    def test_all_expected_values_exist(self) -> None:
        assert ExtractionStatus.PENDING == "pending"
        assert ExtractionStatus.RUNNING == "running"
        assert ExtractionStatus.SUCCESS == "success"
        assert ExtractionStatus.FAILED == "failed"
        assert ExtractionStatus.SKIPPED == "skipped"

    def test_is_str_enum(self) -> None:
        assert isinstance(ExtractionStatus.SUCCESS, str)

    def test_five_members(self) -> None:
        assert len(ExtractionStatus) == 5


class TestIndicatorModel:
    def test_table_name(self) -> None:
        assert Indicator.__tablename__ == "indicator"

    def test_instantiation_with_required_fields(self) -> None:
        now = datetime.now(UTC)
        row = Indicator(
            indicator_id="employment_rate",
            indicator_name="Employment rate",
            geography_code="E08000032",
            geography_name="Bradford",
            geography_level="lad",
            lad_code="E08000032",
            lad_name="Bradford",
            reference_period=date(2023, 1, 1),
            value=72.1,
            source="nomis",
            dataset_code="eejer",
            breakdown_category="",
            is_forecast=False,
            created_at=now,
            updated_at=now,
        )
        assert row.indicator_id == "employment_rate"
        assert row.geography_code == "E08000032"
        assert row.value == pytest.approx(72.1)

    def test_value_can_be_none(self) -> None:
        now = datetime.now(UTC)
        row = Indicator(
            indicator_id="x",
            indicator_name="x",
            geography_code="E08000032",
            geography_name="Bradford",
            geography_level="lad",
            lad_code="E08000032",
            lad_name="Bradford",
            reference_period=date(2023, 1, 1),
            value=None,
            breakdown_category="",
            is_forecast=False,
            created_at=now,
            updated_at=now,
        )
        assert row.value is None

    def test_has_upsert_index(self) -> None:
        index_names = {idx.name for idx in Indicator.__table__.indexes}
        assert "ix_indicator_upsert_key" in index_names

    def test_upsert_index_is_unique(self) -> None:
        upsert_idx = next(
            idx for idx in Indicator.__table__.indexes if idx.name == "ix_indicator_upsert_key"
        )
        assert upsert_idx.unique is True


class TestDatasetMetadataModel:
    def test_table_name(self) -> None:
        assert DatasetMetadata.__tablename__ == "dataset_metadata"

    def test_instantiation(self) -> None:
        now = datetime.now(UTC)
        record = DatasetMetadata(
            dataset_code="eejer",
            source="nomis",
            extraction_status=ExtractionStatus.SUCCESS,
            rows_extracted=22,
            rows_loaded=22,
            created_at=now,
        )
        assert record.dataset_code == "eejer"
        assert record.extraction_status == ExtractionStatus.SUCCESS

    def test_optional_fields_default_to_none(self) -> None:
        record = DatasetMetadata(
            dataset_code="x",
            source="x",
            extraction_status=ExtractionStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        assert record.error_message is None
        assert record.prefect_flow_run_id is None
        assert record.source_url is None


class TestJobsLsoaModel:
    def test_table_name(self) -> None:
        assert JobsLsoa.__tablename__ == "jobs_lsoa"

    def test_instantiation(self) -> None:
        now = datetime.now(UTC)
        row = JobsLsoa(
            lsoa_code="E01007434",
            lsoa_name="Bradford 001A",
            msoa_code="E02006868",
            msoa_name="Bradford 001",
            lad_code="E08000032",
            lad_name="Bradford",
            year=2022,
            sic_code=1629,
            sic_description="Support activities",
            section="Agriculture",
            division="Division 1",
            group_name="Group 1",
            employees=50,
            created_at=now,
            updated_at=now,
        )
        assert row.lsoa_code == "E01007434"
        assert row.employees == 50

    def test_employees_can_be_none(self) -> None:
        now = datetime.now(UTC)
        row = JobsLsoa(
            lsoa_code="E01007434",
            lsoa_name="x",
            msoa_code="E02006868",
            msoa_name="x",
            lad_code="E08000032",
            lad_name="Bradford",
            year=2022,
            sic_code=1629,
            sic_description="x",
            section="x",
            division="x",
            group_name="x",
            employees=None,
            created_at=now,
            updated_at=now,
        )
        assert row.employees is None


class TestIndustryBusinessModel:
    def test_table_name(self) -> None:
        assert IndustryBusiness.__tablename__ == "industry_business"

    def test_instantiation(self) -> None:
        now = datetime.now(UTC)
        row = IndustryBusiness(
            year=2022,
            msoa_code="E02006868",
            msoa_name="Bradford 001",
            lad_code="E08000032",
            lad_name="Bradford",
            industry="Manufacturing",
            turnover_band="Micro under 250k",
            business_count=12,
            created_at=now,
            updated_at=now,
        )
        assert row.industry == "Manufacturing"
        assert row.business_count == 12


class TestIndustryBusinessKpiModel:
    def test_table_name(self) -> None:
        assert IndustryBusinessKpi.__tablename__ == "industry_business_kpi"

    def test_instantiation(self) -> None:
        now = datetime.now(UTC)
        row = IndustryBusinessKpi(
            grouping_level="lad",
            year=2022,
            lad_code="E08000032",
            lad_name="Bradford",
            msoa_code="",
            msoa_name="",
            industry="Manufacturing",
            turnover_band="Micro under 250k",
            business_count=100,
            pct_change_3y=5.2,
            pct_change_8y=-1.1,
            created_at=now,
            updated_at=now,
        )
        assert row.grouping_level == "lad"
        assert row.pct_change_3y == pytest.approx(5.2)


class TestGeoLookupModel:
    def test_table_name(self) -> None:
        assert GeoLookup.__tablename__ == "geo_lookup"

    def test_instantiation(self) -> None:
        row = GeoLookup(
            lsoa_code="E01000001",
            lsoa_name="Area 001A",
            msoa_code="E02000001",
            msoa_name="MSOA 001",
            lad_code="E06000001",
            lad_name="LAD One",
            region_code="E12000001",
            region_name="North East",
        )
        assert row.lsoa_code == "E01000001"
        assert row.lad_code == "E06000001"

    def test_region_fields_can_be_none(self) -> None:
        row = GeoLookup(
            lsoa_code="E01000001",
            lsoa_name="Area 001A",
            msoa_code="E02000001",
            msoa_name="MSOA 001",
            lad_code="E06000001",
            lad_name="LAD One",
            region_code=None,
            region_name=None,
        )
        assert row.region_code is None
