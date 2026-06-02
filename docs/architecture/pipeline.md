# Pipeline

The pipeline is built with [Prefect](https://www.prefect.io/), a workflow orchestration tool. Prefect handles scheduling, retries, logging, and provides the UI where you can monitor every run.

---

## Flows

The pipeline is made up of 15 flows, grouped into three domains. Each flow handles one dataset or group of related datasets.

### Economy

| Flow | What it does | Source | Status |
|------|-------------|--------|--------|
| `economy-employment-jobs` | Employment rate, unemployment rate, self-employment rate, economic inactivity rate, jobs density | NOMIS | Live - runs monthly |
| `economy-earnings` | Median gross weekly earnings | NOMIS | Live - runs monthly |
| `economy-claimant-count` | Children in low income families, PIP claimants | DWP Stat-Xplore | Live - runs monthly |
| `economy-business-demography` | Business births, deaths, and survival rates | ONS | Static - data loaded manually |
| `economy-gdp-gva` | Gross Value Added by LAD | ONS | Static - data loaded manually |

### Society

| Flow | What it does | Source | Status |
|------|-------------|--------|--------|
| `society-health-outcomes` | Life expectancy, healthy life expectancy, preventable mortality | NHS Fingertips | Live - runs monthly |
| `society-education-attainment` | RQF4+ qualifications, no qualifications | NOMIS | Live - runs monthly |
| `society-housing-tenure` | Owner-occupied, private rented, social housing | ONS | Static - data loaded manually |
| `society-deprivation-imd` | Index of Multiple Deprivation | ONS | Static - data loaded manually |
| `society-crime-statistics` | Crime rates by type | Home Office | Static - data loaded manually |
| `society-physical-activity` | Physical activity participation rates | Sport England | Static - data loaded manually |
| `society-digital-inclusion` | Broadband coverage and speeds | Ofcom | Static - data loaded manually |

### Environment

| Flow | What it does | Source | Status |
|------|-------------|--------|--------|
| `environment-air-quality` | Annual mean PM2.5, PM10, NO2 concentrations | DEFRA AURN | Static - data loaded manually |
| `environment-energy-consumption` | Sub-national electricity and gas consumption | BEIS/DESNZ | Static - data loaded manually |

There is also an `orchestrator-full-refresh` flow that triggers all 14 domain flows in sequence.

---

## Schedule

All flows are scheduled to run on the 1st of each month at 06:00 Europe/London time.

Static flows still run on this schedule, but they log a message and exit immediately - the data they serve is pre-loaded from CSV files and only needs refreshing when a new edition of the source data is published.

---

## What happens when a flow fails

1. The flow retries once automatically after five minutes.
2. If it still fails, an email alert is sent to the configured address (see [Email alerts](../how-to/email-alerts.md)).
3. The failure is recorded in the `dataset_metadata` table with the error message.
4. The next scheduled run will attempt the flow again.

No data in the database is corrupted by a failure - the pipeline uses an upsert operation, so a failed run simply means the latest data was not loaded.

---

## Monitoring flows in the Prefect UI

Open the Prefect UI at `http://localhost:4200` (via SSH tunnel - see [Onboarding](../onboarding.md)).

From there you can:

- See the status of every past and current run
- Filter runs by domain using the tags: `economy`, `society`, `environment`, `orchestrator`
- Click into any run to read the logs and error messages
- Manually trigger a run (see [Re-run a flow manually](../how-to/re-run-a-flow.md))
