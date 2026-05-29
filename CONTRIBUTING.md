# Contributing to YHODA Pipeline

Thank you for contributing to the Yorkshire Vitality Observatory ETL pipeline.
Please read this guide before opening a PR.

---

## Branching strategy

| Branch | Purpose |
|--------|---------|
| `main` | Production — protected; all changes via PR |
| `feature/<ticket>-<slug>` | New functionality |
| `fix/<ticket>-<slug>` | Bug fixes |
| `chore/<slug>` | Non-functional changes (deps, docs, CI) |
| `migration/<slug>` | Database schema changes |

```
main ◄── feature/42-add-crime-flow
     ◄── fix/67-normalise-null-handling
     ◄── migration/add-geo-region-col
```

---

## Development setup

```bash
# 1. Fork & clone
git clone https://github.com/your-fork/YHODA.git
cd YHODA

# 2. Install all dependencies (including dev extras)
uv sync --extra dev

# 3. Copy and fill in environment variables
cp .env.example .env
```

---

## Commands reference

### Linting and formatting

```bash
# Check for lint errors
uv run ruff check src/ tests/

# Auto-fix safe lint issues
uv run ruff check --fix src/ tests/

# Format code
uv run ruff format src/ tests/

# Type check
uv run mypy src/
```

### Tests

```bash
# Run the full test suite
uv run pytest

# With coverage report
uv run pytest --cov=src/yhovi_pipeline --cov-report=term-missing

# Run only unit tests (no DB/API required)
uv run pytest tests/unit/

# Run a single test file
uv run pytest tests/unit/test_config.py -v
```

For the unit tests to run without a real database, the following env vars
must be set (dummy values are fine):

```bash
export DATABASE_URL="postgresql+psycopg2://t:t@localhost/d"
export DWP_API_KEY="x"
uv run pytest tests/unit/
```

### Database migrations

```bash
# Generate a new migration from ORM model changes
uv run alembic revision --autogenerate -m "describe what changed"

# Apply all pending migrations
uv run alembic upgrade head

# Roll back one revision
uv run alembic downgrade -1

# Show migration history
uv run alembic history --verbose
```

### Prefect deployments

```bash
# Register all deployments with the Prefect server
uv run prefect deploy --all --no-prompt

# Run a specific flow manually (for testing)
uv run prefect run deployment 'economy/employment-jobs'
```

---

## PR checklist

Before opening a pull request, confirm that:

- [ ] Code passes `ruff check src/ tests/` with no errors
- [ ] Code is formatted with `ruff format src/ tests/`
- [ ] `mypy src/` reports no errors
- [ ] All new logic has corresponding unit tests in `tests/unit/`
- [ ] If ORM models changed, a new Alembic migration has been generated and tested
- [ ] `prefect.yaml` is updated if a new flow/deployment was added
- [ ] Docstrings are present on all public functions and classes
- [ ] The PR description explains *why* the change is needed, not just *what* changed

---

## Code conventions

### Flows

- Use `@flow(name="<domain>/<slug>", retries=1, task_runner=ThreadPoolTaskRunner(max_workers=4))`
- Flow names must match the `name:` key in `prefect.yaml`
- Flows orchestrate tasks — business logic lives in tasks

### Tasks

- Use `@task(name="<layer>/<source>/<action>", retries=3, retry_delay_seconds=60)`
- Tasks should be small and single-purpose
- Return typed DataFrames or ORM instances; avoid returning `None` from data tasks

### Settings

- Always access configuration via `get_settings()` — never read `os.environ` directly in
  flows or tasks
- Exception: `db/migrations/env.py` reads env vars directly to avoid requiring API keys
  for migrations

### Secrets

- All secrets are `pydantic.SecretStr` — call `.get_secret_value()` only at the call site
- Never log secret values

---

## Releases

Releases are automated via release-please and Conventional Commits — no manual version bumping
is needed. See [RELEASING.md](RELEASING.md) for the full workflow.

---

## Getting help

Open a GitHub Discussion or tag `@team-data-engineering` in your PR.
