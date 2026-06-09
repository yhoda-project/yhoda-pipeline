# API Key Has Expired

Use this runbook if a flow is failing with an authentication error (`HTTP 401`, "invalid API key", or similar), or if you need to rotate an API key as a precaution.

The pipeline uses two API keys: one for DWP Stat-Xplore (required) and one for NOMIS (optional).

---

## DWP Stat-Xplore API key

### Getting a new key

1. Go to [stat-xplore.dwp.gov.uk](https://stat-xplore.dwp.gov.uk/) and sign in
2. Go to your account settings and generate a new API key
3. Copy the key immediately - it is only shown once

### Updating the key on the VM

Connect to the staging VM:

```bash
ssh <your_username>@yhoda-staging.shef.ac.uk
```

Open the `.env` file and update `DWP_API_KEY=` with the new value. Save and exit.

Repeat on the production VM (`yhoda-prod.shef.ac.uk`).

### Verifying it works

Trigger the claimant-count flow manually and check the logs:

```bash
uv run python -c "
from yhovi_pipeline.flows.economy.claimant_count import claimant_count_flow
claimant_count_flow()
"
```

If the run succeeds, the key is working.

---

## NOMIS API key

NOMIS public endpoints work without an API key - the key only removes rate limits. If a NOMIS flow is failing with a rate limit error (`HTTP 429`), the key may have expired.

### Getting a new key

1. Register or sign in at [nomisweb.co.uk](https://www.nomisweb.co.uk/)
2. Go to My Account → API key
3. Copy the key

### Updating the key on the VM

Open the `.env` file on both VMs and update the `NOMIS_API_KEY=` line, following the same steps as above.

### Verifying it works

Trigger the earnings flow manually:

```bash
uv run python -c "
from yhovi_pipeline.flows.economy.earnings import earnings_flow
earnings_flow()
"
```

---

## If the key has been compromised

If a key has been accidentally committed to GitHub or otherwise exposed, revoke it immediately via the relevant portal and generate a new one before updating the `.env` files.
