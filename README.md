# Yorkshire Vitality Observatory — Data Pipeline

> YHODA — Yorkshire & Humber Office for Data Analytics
> A Prefect v3 ETL pipeline that collects, transforms, and warehouses socioeconomic,
> health, and environmental indicators for Yorkshire Local Authority Districts into a
> central PostgreSQL database.

This pipeline underpins the [Yorkshire Engagement Portal](https://yorkshireportal.org/)
and its [Yorkshire Vitality Suite](https://yorkshireportal.org/vitality-suite) dashboards.

---

## What This Pipeline Does

Each month the pipeline automatically:

1. Pulls fresh data from source APIs (e.g. NOMIS labour market statistics)
2. Validates and normalises the data into a consistent schema
3. Upserts the results into a PostgreSQL data warehouse
4. Logs each run's status, row counts, and any errors

Static datasets (preprocessed CSVs on the shared drive) are loaded once per
environment using the utility scripts described below.

---

## What's in the Database

The database holds indicators across three domains, covering all 22 Yorkshire LADs,
with data at LAD, MSOA, and LSOA geography levels.

| Domain | Examples |
|--------|----------|
| Economy | Employment rate, median weekly earnings, business counts, jobs by SIC code |
| Society | Life expectancy, healthy life expectancy, qualifications, LSOA neighbourhood indicators |
| Environment | Greenhouse gas emissions, healthy life expectancy by sex |

Full indicator list: see [`src/yhovi_pipeline/utils/load_csv.py`](src/yhovi_pipeline/utils/load_csv.py) → `DATASET_REGISTRY`.

### Database tables

| Table | Purpose |
|-------|---------|
| `indicator` | Central fact table — one row per indicator × geography × period × breakdown category |
| `dataset_metadata` | Audit log of every pipeline run (rows loaded, status, errors) |
| `geo_lookup` | LSOA → MSOA → LAD → Region hierarchy for geography aggregation |
| `jobs_lsoa` | LSOA-level employee counts by SIC code (Jobs dashboard) |
| `industry_business` | MSOA-level business counts by industry and turnover band (Industry dashboard) |
| `industry_business_kpi` | Pre-aggregated 3-year and 8-year business change KPIs (Industry dashboard) |

See [docs/entity-relationship-diagram.md](docs/entity-relationship-diagram.md) for the full ERD.

The upsert key on `indicator` is `(indicator_id, geography_code, reference_period, breakdown_category)` —
re-running a flow updates existing rows rather than creating duplicates.

---

## Architecture

```
Source APIs / CSVs
        │
        ▼
  [ Extract tasks ]   ← tasks/extract/  (one module per source)
        │
        ▼
  [ Transform tasks ] ← tasks/transform/  validate → normalise → geo
        │
        ▼
  [ Load tasks ]      ← tasks/load/database.py  (PostgreSQL upsert)
        │
        ▼
  PostgreSQL warehouse
        │
        ▼
  Power BI dashboards (Yorkshire Vitality Suite)
```

### Flows and their automation status

| Flow | Datasets | Source | Status |
|------|----------|--------|--------|
| `economy/employment-jobs` | Employment, unemployment, self-employment, inactivity rates | Nomis APS | Live — runs monthly |
| `economy/earnings` | Median gross weekly pay | Nomis ASHE | Live — runs monthly |
| `society/education-attainment` | RQF4+ qualifications, no qualifications | Nomis APS | Live — runs monthly |
| `society/health-outcomes` | Life expectancy (M/F), healthy life expectancy (M/F), preventable mortality | NHS Fingertips | Live — runs monthly |
| `economy/claimant-count` | Children in low income, PIP claimants | DWP Stat-Xplore | Pending API key |
| All others | Business demography, GVA, housing, crime, environment, etc. | ONS, DfE, Ofcom, BEIS, Sport England | Static — loaded from CSV; no live API |

All live deployments run on the 1st of each month at 06:00 Europe/London.

---

## Quickstart (for developers on the VM)

### Prerequisites

- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv) package manager
- PostgreSQL 14+ with the target database created
- Self-hosted Prefect v3 server

### 1. Clone and install

```bash
git clone https://github.com/yhoda-project/YHODA.git
cd YHODA
uv sync --extra dev
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — at minimum set DATABASE_URL
```

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | SQLAlchemy URL, e.g. `postgresql+psycopg2://user:pass@host/dbname` |
| `DWP_API_KEY` | No | DWP Stat-Xplore API key (only needed for claimant-count flow) |
| `NOMIS_API_KEY` | No | Nomis API key — public endpoints work without one, key gives higher rate limits |
| `PREFECT_API_URL` | No | URL of your Prefect server (only needed to register/run deployments) |
| `PREFECT_WORK_POOL` | No | Prefect work pool name (default: `yhovi-default`) |
| `LOG_LEVEL` | No | Python logging level (default: `INFO`) |

### 3. Run database migrations

```bash
uv run alembic upgrade head
```

### 4. (One-time) Seed the geography lookup table

```bash
uv run python -m yhovi_pipeline.utils.seed_geo_lookup
```

Loads the ONS LSOA → MSOA → LAD hierarchy. Only needed once per environment.

### 5. (One-time) Load historical data from preprocessed CSVs

```bash
# Indicator-level data (LAD geography)
uv run python -m yhovi_pipeline.utils.load_csv

# Jobs dashboard (LSOA-level employee counts by SIC code)
uv run python -m yhovi_pipeline.utils.load_jobs

# Industry dashboard (MSOA-level business counts + KPIs)
uv run python -m yhovi_pipeline.utils.load_industry

# Neighbourhoods dashboard (LSOA-level indicators)
uv run python -m yhovi_pipeline.utils.load_neighbourhoods
```

All loaders read from the shared drive (`/mnt/yhoda_drive/Shared/`). Only needed
once per environment — thereafter the monthly flows keep indicator data current.
The Jobs, Industry, and Neighbourhoods loaders should be re-run whenever new
versions of the source CSVs are placed on the shared drive.

### 6. Register deployments with Prefect

```bash
uv run prefect deploy --all --no-prompt
```

### 7. Verify

```bash
uv run python -c "from yhovi_pipeline.config import get_settings; print('ok')"
uv run pytest
uv run ruff check src/ tests/
```

---

## Running a Flow Manually

To trigger a flow outside its monthly schedule (e.g. to backfill historical data):

```bash
# Backfill employment rates for all available years
uv run python -c "
from yhovi_pipeline.flows.economy.employment_jobs import employment_jobs_flow
employment_jobs_flow(time='2004-12-2024-12')
"

# Pull latest earnings data
uv run python -c "
from yhovi_pipeline.flows.economy.earnings import earnings_flow
earnings_flow()
"
```

The `time` parameter accepts:
- `"latest"` — most recent period only (default)
- `"2023-12"` — a specific period
- `"2004-12-2024-12"` — a full date range (Nomis flows only)

---

## Project Structure

```
YHODA/
├── src/
│   └── yhovi_pipeline/
│       ├── config.py                  # Settings via pydantic-settings; use get_settings()
│       ├── db/
│       │   ├── models.py              # ORM: Indicator, DatasetMetadata, GeoLookup,
│       │   │                          #       JobsLsoa, IndustryBusiness, IndustryBusinessKpi
│       │   └── migrations/            # Alembic migration history
│       ├── flows/
│       │   ├── economy/               # employment_jobs, earnings, claimant_count, business_demography, gdp_gva
│       │   ├── society/               # health_outcomes, education_attainment, housing_tenure,
│       │   │                          #   deprivation_imd, crime_statistics, physical_activity, digital_inclusion
│       │   └── environment/           # air_quality, energy_consumption
│       ├── tasks/
│       │   ├── extract/               # nomis, fingertips, dwp, ons, sport_england, ofcom, defra, beis
│       │   ├── transform/             # validate, normalise, geo
│       │   └── load/                  # database (upsert_indicators, write_metadata)
│       └── utils/
│           ├── load_csv.py            # One-time loader for indicator-level CSVs
│           ├── load_jobs.py           # One-time loader for jobs_lsoa (Jobs dashboard)
│           ├── load_industry.py       # One-time loader for industry_business + KPI tables
│           ├── load_neighbourhoods.py # One-time loader for LSOA indicator data
│           ├── seed_geo_lookup.py     # One-time geo hierarchy seeder
│           └── geo_lookups.py         # LRU-cached LSOA → LAD lookup
├── docs/
│   ├── entity-relationship-diagram.md # Database ERD (Mermaid)
│   └── tutorial-pgadmin.md            # How to connect and query the database with pgAdmin
├── tests/
│   ├── unit/
│   └── integration/
├── .github/workflows/ci.yml           # lint → test → deploy on push to main
├── .pre-commit-config.yaml            # ruff, mypy, and file hygiene hooks
├── prefect.yaml                       # Prefect deployment definitions
├── alembic.ini
├── pyproject.toml
└── .env.example
```

---

## Development

```bash
# Lint and auto-fix
uv run ruff check --fix src/ tests/
uv run ruff format src/ tests/

# Type check
uv run mypy src/

# Tests
uv run pytest
uv run pytest --cov=src/yhovi_pipeline   # with coverage

# Database migrations
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
uv run alembic downgrade -1              # roll back one revision
```

Unit tests require env vars but no real database:

```bash
export DATABASE_URL="postgresql+psycopg2://t:t@localhost/d"
export DWP_API_KEY="x"
uv run pytest tests/unit/
```

CI runs on every push and pull request. Deployments to Prefect are triggered
automatically on merge to `main`.

---

## How to Add a New Data Source

1. Create an extract task in `tasks/extract/<source>.py` — follow the Nomis module as a template. Use `@task(name="extract/<source>/...", retries=3, retry_delay_seconds=60)`.

2. Add a normaliser in `tasks/transform/normalise.py` if the source has a non-standard date or value format.

3. Create a flow in the appropriate domain directory. Use `@flow(name="<domain>/<name>", task_runner=ThreadPoolTaskRunner(max_workers=4))`.

4. Register the deployment in `prefect.yaml` following the existing pattern.

5. Add the indicator(s) to `DATASET_REGISTRY` in `utils/load_csv.py`.

6. Write unit tests in `tests/unit/` for your transform logic.

7. Open a PR — CI will lint, test, and deploy automatically on merge.

---

## Links

- [Yorkshire Engagement Portal](https://yorkshireportal.org/)
- [Yorkshire Vitality Suite](https://yorkshireportal.org/vitality-suite)
- [YHODA](https://yhoda.sites.sheffield.ac.uk/about-us)
- [Nomis API docs](https://www.nomisweb.co.uk/api/v01/help)
- [NHS Fingertips API](https://fingertips.phe.org.uk/api)

---

## Licence

See [LICENSE](LICENSE).
