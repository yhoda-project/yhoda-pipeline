"""Unit tests for yhovi_pipeline.config."""

from __future__ import annotations

from yhovi_pipeline.config import YORKSHIRE_LAD_CODES, Settings, get_settings


def test_yorkshire_lad_codes_count() -> None:
    """There should be exactly 22 Yorkshire LAD codes."""
    assert len(YORKSHIRE_LAD_CODES) == 22


def test_yorkshire_lad_codes_format() -> None:
    """All LAD codes should start with 'E' and be 9 characters long."""
    for code in YORKSHIRE_LAD_CODES:
        assert code.startswith("E"), f"LAD code {code!r} does not start with 'E'"
        assert len(code) == 9, f"LAD code {code!r} is not 9 characters"


def test_settings_instantiation(test_settings: Settings) -> None:
    """Settings should instantiate correctly from the test fixture."""
    assert test_settings.log_level == "DEBUG"
    assert test_settings.prefect_work_pool == "yhovi-default"
    assert test_settings.database_url is not None
    assert test_settings.dwp_api_key is not None


def test_get_settings_cached(test_settings: Settings) -> None:
    """get_settings() should return the same instance on repeated calls."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_settings_yorkshire_lad_codes(test_settings: Settings) -> None:
    """Settings should expose the 22 Yorkshire LAD codes by default."""
    assert len(test_settings.yorkshire_lad_codes) == 22
