# Connect Power BI to the Database

This guide explains how to connect Power BI Desktop to the YHODA PostgreSQL database.

You will need an active VPN connection and an SSH tunnel before Power BI can reach the database. The tunnel setup is the same as for pgAdmin - see [Query the database](query-the-database.md) for a detailed explanation.

---

## What you need

- Power BI Desktop installed on your laptop
- University of Sheffield VPN connected
- Your SSH username and password for the VM
- Your database username and password

---

## Step 1 - Connect to the VPN

Ensure you have connected to the University of Sheffield VPN before doing anything else.

---

## Step 2 - Open an SSH tunnel

Open a terminal and run:

```bash
ssh -L 5433:127.0.0.1:5432 <your_username>@yhoda-staging.shef.ac.uk -N -o ServerAliveInterval=60
```

Replace `<your_username>` with your VM username. Enter your password and approve the Duo push when prompted.

Leave the terminal open. Closing it closes the tunnel and Power BI will lose its connection.

> Use `yhoda-prod.shef.ac.uk` instead if you are connecting to the production database.

---

## Step 3 - Connect Power BI to the database

1. Open Power BI Desktop
2. Click Get data → More → Database → PostgreSQL database → Connect
3. Enter the following:

| Field | Value |
|-------|-------|
| Server | `127.0.0.1:5433` |
| Database | `yhoda_dev` (staging) or `yhoda_prod` (production) |

4. Click OK
5. When prompted for credentials, select Database and enter your PostgreSQL username and password
6. Click Connect

Power BI will show a Navigator panel listing the available tables. Select the tables you need and click Load or Transform Data.

---

## Connection details

| Setting | Value |
|---------|-------|
| Host | `127.0.0.1` |
| Port | `5433` |
| Database | `yhoda_dev` (staging) or `yhoda_prod` (production) |
| Authentication | Database (username and password) |

---

## Keeping the connection active

Power BI will lose its connection if the SSH tunnel closes. Re-open the tunnel and refresh the report to reconnect.

If you want Power BI to refresh automatically on a schedule via Power BI Service, you will need a data gateway. Speak to the YHODA technical team about this.

> The VPN and SSH tunnel must both be active whenever Power BI needs to connect to the database.
