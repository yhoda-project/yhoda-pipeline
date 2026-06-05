# Pipeline Has Stopped Running

Use this runbook if no flows have run on their expected schedule - for example, it is the 3rd of the month and none of the 1st-of-month flows have a recent entry in the Prefect UI.

---

## Step 1 - Confirm that flows have not run

Open the Prefect UI at [http://localhost:4200](http://localhost:4200) and click Flow Runs. Filter by date. If there are no recent runs, continue to Step 2.

You can also check the database:

```sql
SELECT dataset_code, extraction_status, created_at
FROM dataset_metadata
ORDER BY created_at DESC
LIMIT 10;
```

If the most recent entries are from a previous month, the pipeline is not running.

---

## Step 2 - Check the Prefect worker is running

The Prefect worker is a process that runs on the VM and picks up scheduled flow runs. If it has stopped, no flows will run.

Connect to the production VM:

```bash
ssh <your_username>@yhoda-prod.shef.ac.uk
```

Check whether the worker process is running:

```bash
ps aux | grep "prefect worker"
```

If you see no output (other than the grep line itself), the worker is not running.

---

## Step 3 - Restart the worker

Start the worker on the VM:

```bash
cd /path/to/YHODA
uv run prefect worker start --pool yhovi-default
```

Leave this running in a terminal session. If you are working over SSH and want the process to persist after you disconnect, attach it to a `screen` or `tmux` session.

Check the Prefect UI - within a few minutes, any overdue scheduled runs should begin.

---

## Step 4 - Check the work pool

In the Prefect UI, click Work Pools in the left sidebar. The `yhovi-default` pool should show as Ready. If it shows as Paused, click on it and unpause it.

---

## Step 5 - Check the deployments are registered

In the Prefect UI, click Deployments. You should see all 15 deployments listed. If any are missing, re-register them from the VM:

```bash
uv run prefect deploy --all --no-prompt
```

---
