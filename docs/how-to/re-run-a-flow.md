# Re-run a Flow Manually

You might want to re-run a flow outside its monthly schedule to:

- Retry a flow that failed in the previous run
- Backfill historical data after an initial setup
- Test that a code change has fixed a problem

---

## From the Prefect UI

1. Open the Prefect UI at [http://localhost:4200](http://localhost:4200) (SSH tunnel required - see [Onboarding](../onboarding.md))
2. Click Deployments in the left sidebar
3. Find the flow you want to run (filter by tag: `economy`, `society`, `environment`)
4. Click the run button (the play icon) on the right
5. In the Run now dialog, leave the defaults and click Run

The run will appear under Flow Runs within a few seconds. Click on it to watch the live logs.

---

## From the command line

Connect to the staging or production VM via SSH, then run the flow directly.

### Run with default settings (latest data only)

```bash
uv run python -c "
from yhovi_pipeline.flows.economy.earnings import earnings_flow
earnings_flow()
"
```

### Backfill a range of historical data

NOMIS flows accept a `time` parameter for historical ranges:

```bash
uv run python -c "
from yhovi_pipeline.flows.economy.employment_jobs import employment_jobs_flow
employment_jobs_flow(time='2004-12-2024-12')
"
```

| `time` value | Meaning |
|-------------|---------|
| `"latest"` | Most recent period only (default) |
| `"2023-12"` | A specific period |
| `"2004-12-2024-12"` | A full date range |

---

## Which flows support historical backfill?

Only NOMIS flows support the `time` parameter for date ranges. These are:

- `employment_jobs_flow`
- `earnings_flow`
- `education_attainment_flow`

Flows pulling from NHS Fingertips always fetch the full historical series automatically. DWP flows fetch the most recent 12 periods by default.
