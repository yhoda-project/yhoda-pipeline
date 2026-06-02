# Environment Variables

All configuration for the pipeline is set via environment variables in the `.env` file on the VM. Copy `.env.example` to `.env` and fill in the values.

Never commit `.env` to GitHub - it contains credentials and is already listed in `.gitignore`.

---

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string. Format: `postgresql+psycopg2://user:password@host:5432/dbname` |
| `DWP_API_KEY` | Yes | - | DWP Stat-Xplore API key. Request from [stat-xplore.dwp.gov.uk](https://stat-xplore.dwp.gov.uk/) |
| `NOMIS_API_KEY` | No | - | NOMIS API key. Public endpoints work without one; the key removes rate limits |
| `PREFECT_API_URL` | No | - | URL of the self-hosted Prefect server, e.g. `http://127.0.0.1:4200/api` |
| `PREFECT_WORK_POOL` | No | `yhovi-default` | Prefect work pool name. Must exist on the Prefect server |
| `SMTP_USERNAME` | No | - | University of Sheffield email address used to send pipeline alert emails |
| `SMTP_PASSWORD` | No | - | Google App Password for the above address - see [Email alerts](../how-to/email-alerts.md) |
| `ALERT_GROUP_EMAIL` | No | - | Recipient address(es) for pipeline alerts. Comma-separated list supported |
| `ALERT_SUCCESS_ENABLED` | No | `false` | Set to `true` to receive an email on every successful flow run |
| `LOG_LEVEL` | No | `INFO` | Python logging level. Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
