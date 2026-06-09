# Onboarding

This page walks a new developers through everything needed to get set up on the YHODA pipeline.

---

## What you'll need access to

| System | How to get access |
|--------|------------------|
| VM - staging (`yhoda-staging.shef.ac.uk`) | Ask the VM admin to raise a TopDesk ticket with University of Sheffield IT Services |
| VM - production (`yhoda-prod.shef.ac.uk`) | Same as above - request both at the same time |
| PostgreSQL database | Ask an existing team member to create credentials for you (see below) |
| Prefect UI | No credentials needed - it's served locally on the VM via SSH tunnel (see below) |
| GitHub repository | Request access to [yhoda-project/yhoda-pipeline](https://github.com/yhoda-project/yhoda-pipeline) from an existing team member |

Allow a few working days for the TopDesk ticket to be fulfilled.

---

## 1. VM access

Once IT have provisioned your account, you'll receive an SSH username (e.g. `sa_abc1xyz`).

Connect using:

```bash
ssh <your_username>@yhoda-staging.shef.ac.uk
```

You'll be prompted for your password and a Duo two-factor push.

> The University of Sheffield VPN must be active before you can reach either VM.
> Connect to the VPN first, every time.

---

## 2. PostgreSQL database credentials

A team member with admin access to the database will need to create a user for you.
Share your preferred username with them and they'll provide you with a password.

Once you have credentials, follow the [Querying the Database](how-to/query-the-database.md)
tutorial to connect via pgAdmin from your laptop.

---

## 3. Clone the repository and configure your environment

```bash
git clone https://github.com/yhoda-project/yhoda-pipeline.git
cd yhoda-pipeline
cp .env.example .env
```

Open `.env` and fill in your credentials. The table below describes every variable:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | SQLAlchemy connection string for the PostgreSQL database |
| `SHARED_DRIVE_PATH` | Yes (loaders) | Absolute path to the root of the YHODA shared drive on the VM - required to run any CSV loader |
| `DWP_API_KEY` | Yes | DWP Stat-Xplore API key - request from the DWP Stat-Xplore portal |
| `NOMIS_API_KEY` | No | NOMIS API key - public endpoints work without one, but a key removes rate limits |
| `PREFECT_API_URL` | Yes | URL of the local Prefect server (e.g. `http://127.0.0.1:4200/api`) |
| `PREFECT_WORK_POOL` | No | Prefect work pool name. Defaults to `yhovi-default` if not set |
| `SMTP_USERNAME` | Yes (alerts) | Sheffield University email used to send pipeline alert emails |
| `SMTP_PASSWORD` | Yes (alerts) | Google App Password for the above account - see [Email Alerts](how-to/email-alerts.md) |
| `ALERT_GROUP_EMAIL` | Yes (alerts) | Email address(es) that receive pipeline alerts (comma-separated) |
| `ALERT_SUCCESS_ENABLED` | No | Set to `true` to receive emails on successful runs. Off by default |
| `LOG_LEVEL` | No | Python logging level. Defaults to `INFO` |

Keep `.env` secure - it contains credentials and must never be committed to GitHub.
It is already listed in `.gitignore`.

---

## 4. Install the package

You'll need Python 3.11+ and the [`uv`](https://github.com/astral-sh/uv) package manager.

```bash
uv sync --extra dev
```

Verify the install:

```bash
uv run python -c "from yhovi_pipeline.config import get_settings; print('ok')"
```

---

## 5. Access the Prefect UI

The Prefect server runs locally on the VM. To view it from your laptop, open an SSH tunnel:

```bash
ssh -L 4200:127.0.0.1:4200 <your_username>@yhoda-staging.shef.ac.uk -N -o ServerAliveInterval=60
```

Then open [http://localhost:4200](http://localhost:4200) in your browser.

Leave the terminal open - closing it closes the tunnel.

---

## 6. Run the tests

```bash
uv run pytest
```

All tests should pass before you start making changes.

---

## You're set up

At this point you should have:

- [ ] SSH access to both VMs
- [ ] PostgreSQL credentials and a working pgAdmin connection
- [ ] A cloned repo with a completed `.env` file
- [ ] The package installed and tests passing
- [ ] The Prefect UI accessible in your browser

If anything isn't working, check the [Troubleshooting](runbooks/index.md) section or ask an existing team member.
