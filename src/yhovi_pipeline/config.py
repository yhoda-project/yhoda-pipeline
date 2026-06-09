"""Pipeline-wide configuration via pydantic-settings v2.

Settings are loaded from environment variables (and optionally a `.env` file).
Use `get_settings()` to obtain the singleton instance - it is cached after the
first call so the environment is only parsed once per process.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: All 22 Local Authority Districts that make up the Yorkshire & Humber region.
#: ONS GSS codes (E08/E06/E07 prefix).
YORKSHIRE_LAD_CODES: list[str] = [
    # West Yorkshire (5 metropolitan districts)
    "E08000032",  # Bradford
    "E08000033",  # Calderdale
    "E08000034",  # Kirklees
    "E08000035",  # Leeds
    "E08000036",  # Wakefield
    # South Yorkshire (4 metropolitan districts)
    "E08000016",  # Barnsley
    "E08000017",  # Doncaster
    "E08000018",  # Rotherham
    "E08000019",  # Sheffield
    # East Riding / Hull (2 unitary authorities)
    "E06000010",  # East Riding of Yorkshire
    "E06000011",  # Kingston upon Hull
    # North Yorkshire (1 unitary authority + York)
    "E06000065",  # North Yorkshire
    "E06000014",  # York
    # Humber (2 unitary authorities)
    "E06000012",  # North East Lincolnshire
    "E06000013",  # North Lincolnshire
    # Remaining districts in the Humber sub-region / wider Yorkshire
    # (ceremonial county of Yorkshire - included for completeness)
    "E07000163",  # Craven
    "E07000164",  # Hambleton
    "E07000165",  # Harrogate
    "E07000166",  # Richmondshire
    "E07000167",  # Ryedale
    "E07000168",  # Scarborough
    "E07000169",  # Selby
]


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    """Application-wide settings resolved from environment variables.

    All fields can be overridden by setting the corresponding environment
    variable (case-insensitive).  A `.env` file is also read automatically
    when present - useful for local development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # Database ---------------------------------------------------------------
    database_url: SecretStr
    """SQLAlchemy connection URL for the PostgreSQL data warehouse.

    Example:
        postgresql+psycopg2://user:pass@host:5432/dbname
    """

    # API keys ---------------------------------------------------------------
    nomis_api_key: SecretStr | None = None
    """NOMIS (ONS Labour Market Statistics) API key.  Optional - public
    endpoints work without a key but are rate-limited."""

    dwp_api_key: SecretStr
    """DWP Stat-Xplore API key.  Required."""

    # Prefect ----------------------------------------------------------------
    prefect_work_pool: str = "yhovi-default"
    """Name of the Prefect work pool used by all deployments."""

    # Alerts -----------------------------------------------------------------
    smtp_username: SecretStr | None = None
    """University of Sheffield email address used to send pipeline alerts."""

    smtp_password: SecretStr | None = None
    """Google App Password for the alert sender account."""

    alert_group_email: str | None = None
    """Recipient address for pipeline alerts - single address or comma-separated list."""

    alert_success_enabled: bool = False
    """Set to true to receive an email on every successful flow run."""

    # Logging ----------------------------------------------------------------
    log_level: str = "INFO"
    """Python logging level string (DEBUG, INFO, WARNING, ERROR)."""

    # Data paths -------------------------------------------------------------
    shared_drive_path: str | None = None
    """Absolute path to the root of the YHODA shared drive on the VM.

    Required when running any of the manual CSV loaders (load_csv,
    load_industry, load_jobs, load_neighbourhoods, seed_geo_lookup).

    Example (VM default):
        /mnt/yhoda_drive/Shared
    """

    # Geography --------------------------------------------------------------
    yorkshire_lad_codes: list[str] = YORKSHIRE_LAD_CODES
    """ONS GSS codes for the LADs in scope.  Overridable for testing."""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached `Settings` singleton.

    The first call instantiates and validates `Settings`; subsequent calls
    return the cached instance without re-reading the environment.

    Raises:
        pydantic_core.ValidationError: If required environment variables are
            absent or have invalid values.
    """
    return Settings()  # type: ignore[call-arg]
