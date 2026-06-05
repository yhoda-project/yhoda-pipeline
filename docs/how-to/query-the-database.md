# Query the Database

This guide walks you through connecting to the YHODA staging database from your laptop using pgAdmin. You will need this whenever you want to inspect the data, run queries, or export results.

---

## What you need

- pgAdmin 4 installed on your laptop ([download here](https://www.pgadmin.org/download/))
- A terminal (on Windows: Git Bash or PowerShell; on Mac/Linux: Terminal)
- University VPN connected (required to reach the server)
- Your SSH username and password for `yhoda-staging.shef.ac.uk`
- Your database password

---

## Step 1 - Connect to the VPN

Ensure you have connected to the University of Sheffield VPN before doing anything else. The server is not reachable without it.

---

## Step 2 - Open an SSH tunnel

The database is locked to the server and cannot be reached directly. You need to open a tunnel first.

Open a terminal and run:

```bash
ssh -L 5433:127.0.0.1:5432 <your_username>@yhoda-staging.shef.ac.uk -N -o ServerAliveInterval=60
```

Replace `<your_username>` with your own VM username (e.g. `sa_abc1xyz`).

You will be prompted for:

1. Your SSH password
2. A Duo two-factor authentication push

Once Duo is approved, the terminal will go quiet and appear to do nothing, stating "Success. Logging you in..." - this is correct. Leave it open. Closing it closes the SSH tunnel.

---

## Step 3 - Connect pgAdmin to the database

Open pgAdmin. In the left panel, right-click Servers → Register → Server.

Fill in the following:

General tab

| Field | Value |
|-------|-------|
| Name | yhoda-staging |

Connection tab

| Field | Value |
|-------|-------|
| Host name/address | `127.0.0.1` |
| Port | `5433` |
| Maintenance database | `yhoda_dev` |
| Username | e.g. `sa_test_username` |
| Password | (your database password) |

SSH Tunnel tab - leave completely empty / tunnelling toggled OFF.

Click Save. The server should appear in the left panel with a green connected icon.

> If you see a connection error, check that the terminal from Step 2 is still open and that the VPN is still connected.

---

## Step 4 - Browse the tables

Once connected, in the left panel expand:

```
yhoda-staging → Databases → yhoda_dev → Schemas → public → Tables
```

| Table | What it contains |
|-------|-----------------|
| `indicator` | All socioeconomic indicators (employment, health, earnings, etc.) |
| `jobs_lsoa` | Employee counts by industry at neighbourhood level |
| `industry_business` | Business counts by industry and turnover band at MSOA level |
| `industry_business_kpi` | Pre-calculated 3-year and 8-year business change KPIs |
| `geo_lookup` | Geography reference table (LSOA → MSOA → LAD → Region) |
| `dataset_metadata` | Log of every pipeline run |

To preview any table: right-click it → View/Edit Data → First 100 Rows.

---

## Step 5 - Run a query

Right-click the `yhoda_dev` database → Query Tool. Type or paste a query and press F5 to run it. Results appear in the panel below.

### Useful queries

How many rows are in each table?

```sql
SELECT 'indicator' AS tbl, COUNT(*) FROM indicator
UNION ALL SELECT 'jobs_lsoa', COUNT(*) FROM jobs_lsoa
UNION ALL SELECT 'industry_business', COUNT(*) FROM industry_business
UNION ALL SELECT 'industry_business_kpi', COUNT(*) FROM industry_business_kpi
UNION ALL SELECT 'geo_lookup', COUNT(*) FROM geo_lookup
UNION ALL SELECT 'dataset_metadata', COUNT(*) FROM dataset_metadata;
```

What indicators are loaded and when were they last updated?

```sql
SELECT indicator_id, indicator_name, COUNT(*) AS rows, MAX(updated_at) AS last_updated
FROM indicator
GROUP BY indicator_id, indicator_name
ORDER BY indicator_id;
```

Show all data for a specific local authority:

```sql
SELECT *
FROM indicator
WHERE lad_name = 'Sheffield'
ORDER BY indicator_id, reference_period;
```

When did the pipeline last run and did it succeed?

```sql
SELECT dataset_code, extraction_status, rows_loaded, loaded_at
FROM dataset_metadata
ORDER BY created_at DESC
LIMIT 20;
```

---

## Step 6 - Export results to CSV

After running a query, click the save/download icon (arrow pointing down into a tray) above the results grid.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| pgAdmin shows "connection refused" | The SSH tunnel in Step 2 is not running - go back and open it |
| pgAdmin shows "password authentication failed" | Check the database password is correct in the Connection tab |
| Terminal closes unexpectedly | Re-run the `ssh` command in Step 2 and reconnect in pgAdmin |
| Cannot reach the server at all | Check the VPN is connected |
