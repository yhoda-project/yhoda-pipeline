# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YHODA (Yorkshire & Humber Office for Data Analytics) is a **Prefect v3 ETL pipeline** that collects, transforms, and warehouses socioeconomic, health, and environmental indicators for all 22 Yorkshire Local Authority Districts (LADs) into a PostgreSQL data warehouse. The pipeline supports the [Yorkshire Engagement Portal](https://yorkshireportal.org/) and its [Yorkshire Vitality Suite](https://yorkshireportal.org/vitality-suite) dashboards.

**Current Status:** Phase 1 complete (scaffolding). Phase 2 (implementation) is pending — all flow and task bodies contain `# TODO: implement` stubs.

## Project Context

### Background

YHODA bridges a gap for Yorkshire policymakers who want data-informed decisions but lack technical infrastructure. Currently, dashboards rely on manual data collection via R scripts and CSV files — time-consuming, error-prone, and not scalable. This pipeline automates 70–80% of those workflows.

As the UK's first Regional Office for Data Analytics, YHODA aims to become a national exemplar for evidence-based regional policy.

### Timeline (Jan–Jun 2026)

| Target | Milestone |
|--------|-----------|
| Mid-Feb 2026 | Discovery & design — audit workflows, select priority datasets, draft schema |
| End-Apr 2026 | Prototype ingestion — working API connectors for Nomis/ONS and one DWP dataset |
| End-May 2026 | Scale-out — extend to most priority datasets, improve validation and error handling |
| End-Jun 2026 | Handover — documentation, runbooks, training for YHODA team to maintain independently |

### Key Constraints

- **Geography fragmentation:** Datasets use different boundaries (LAD, LSOA, MSOA, OA). A canonical mapping layer is needed.
- **API credentials:** Nomis/ONS and DWP API access not yet registered.
- **Handover:** Code must be clear enough for a less-technical team to maintain post-project.
- **Scope:** ~40 priority datasets to automate; may narrow if timeline is tight.

### Data Sources

| Source | Data | API |
|--------|------|-----|
| NOMIS | Labour market (BRES, APS) | Nomis API |
| ONS | GVA, demography, census | ONS Open Data |
| DWP | Claimant count | Stat-Xplore API |
| NHS Fingertips | Health outcomes | Fingertips API |
| Sport England | Active Lives | TBC |
| Ofcom | Digital connectivity | Connected Nations |
| DEFRA | Air quality | AURN API |
| BEIS/DESNZ | Energy consumption | TBC |

### Useful Links

- Yorkshire Portal: https://yorkshireportal.org/
- Vitality Suite: https://yorkshireportal.org/vitality-suite
- YHODA: https://yhoda.sites.sheffield.ac.uk/about-us
- Nomis API docs: https://www.nomisweb.co.uk/api/v01/help

## Commands

**Install dependencies:**

```bash
uv sync --extra dev
```

**Lint and type-check:**

```bash
uv run ruff check src/ tests/          # Lint
uv run ruff check --fix src/ tests/    # Auto-fix
uv run ruff format src/ tests/         # Format
uv run mypy src/                       # Type check
```

**Run tests:**

```bash
uv run pytest                                        # All tests
uv run pytest tests/unit/                            # Unit tests only
uv run pytest tests/unit/test_config.py -v          # Single file
uv run pytest --cov=src/yhovi_pipeline               # With coverage
```

Unit tests require env vars (no real DB needed):

```bash
export DATABASE_URL="postgresql+psycopg2://t:t@localhost/d"
export DWP_API_KEY="x"
uv run pytest tests/unit/
```

**Database migrations:**

```bash
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "describe change"
uv run alembic downgrade -1
```

**Prefect deployments:**

```bash
uv run prefect deploy --all --no-prompt
```

## Architecture

### Data Flow

```
8 Source APIs → extract/ tasks → transform/ tasks (validate → normalise → geo) → load/ tasks → PostgreSQL
```

Each source maps to a dedicated extract task in `src/yhovi_pipeline/tasks/extract/`. Flows in `src/yhovi_pipeline/flows/` orchestrate these tasks and are grouped into three domains: `economy/` (4 flows), `society/` (7 flows), `environment/` (2 flows).

### Key Modules

- **`config.py`** — Pydantic Settings singleton. Always use `get_settings()` to access config; never read `os.environ` directly (exception: `db/migrations/env.py`). Secrets are `SecretStr` — call `.get_secret_value()` only at the call site.
- **`db/models.py`** — SQLAlchemy 2.0 ORM with three tables: `Indicator` (fact), `DatasetMetadata` (audit/run history), `GeoLookup` (LSOA→MSOA→LAD→Region dimension).
- **`tasks/transform/`** — `validate.py` (schema & LAD validation), `normalise.py` (canonical Indicator shape), `geo.py` (geography aggregation).
- **`tasks/load/database.py`** — Upserts indicators and writes run metadata.
- **`utils/geo_lookups.py`** — LRU-cached ONS geography lookup; `lsoa_to_lad()` for aggregation.

### Flow/Task Conventions

**Flows:** `@flow(name="<domain>/<slug>", retries=1, task_runner=ThreadPoolTaskRunner(max_workers=4))`. Flow names must match entries in `prefect.yaml`. Flows orchestrate; business logic belongs in tasks.

**Tasks:** `@task(name="<layer>/<source>/<action>", retries=3, retry_delay_seconds=60)`. Tasks are small and single-purpose; return typed DataFrames or ORM instances.

### Database

PostgreSQL via psycopg2. Upsert key on `Indicator` is `(indicator_id, lad_code, reference_period)`. All 22 Yorkshire LAD codes are defined as `YORKSHIRE_LAD_CODES` in `config.py` and used throughout for filtering/validation. `ExtractionStatus` enum uses `native_enum=False` to keep the schema portable across database backends.

### CI/CD

GitHub Actions (`.github/workflows/ci.yml`): lint → test → deploy (deploy only on push to `main`). Alembic migrations are auto-formatted with ruff post-write hooks (configured in `alembic.ini`).

## Environment Variables

See `.env.example`. Required: `DATABASE_URL`, `DWP_API_KEY`. Optional: `NOMIS_API_KEY`, `PREFECT_API_URL`, `PREFECT_WORK_POOL`, `LOG_LEVEL`.