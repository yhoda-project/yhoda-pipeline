# A Flow is Failing

Use this runbook if you received an ERROR email from the pipeline, or if you can see a failed flow run in the Prefect UI.

---

## Step 1 - Confirm the failure

Open the Prefect UI at [http://localhost:4200](http://localhost:4200) (SSH tunnel required - see [Onboarding](../onboarding.md)).

Click Flow Runs in the left sidebar. Failed runs are shown with a red status icon. Note:

- The flow name (e.g. `economy-claimant-count`)
- The time it failed
- The error message shown in the Logs tab

---

## Step 2 - Read the error message

Click on the failed flow run, then click the Logs tab. Look for lines labelled `ERROR` or `CRITICAL` near the bottom of the log.

| Error message | Likely cause |
|--------------|--------------|
| `HTTP 401` or `invalid or missing API key` | The API key for that source has expired or is wrong - see [API key has expired](api-key-expired.md) |
| `HTTP 503` or `connection refused` or `timeout` | The source API is temporarily unavailable - wait and retry |
| `HTTP 429` or `rate limit` | Too many requests were sent - the pipeline will retry automatically |
| `column does not exist` or `unexpected column` | The source API has changed its data format - escalate to the technical team |
| `could not connect to server` or `database connection` | The PostgreSQL database is not reachable - check the VM is running |

---

## Step 3 - Retry the flow

If the cause looks temporary (API down, rate limit, network blip), retry the flow manually:

1. In the Prefect UI, click the failed flow run
2. Click Rerun at the top right
3. Watch the Logs tab for the new run

If it succeeds, no further action is needed.

---

## Step 4 - Check how often this has happened

Query the `dataset_metadata` table to see the history:

```sql
SELECT dataset_code, extraction_status, error_message, created_at
FROM dataset_metadata
WHERE extraction_status = 'failed'
ORDER BY created_at DESC
LIMIT 20;
```

If the same flow has failed multiple times in a row, the cause is unlikely to be temporary.

---
