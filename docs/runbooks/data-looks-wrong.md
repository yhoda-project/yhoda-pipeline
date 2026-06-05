# Data Looks Wrong

Use this runbook if a figure in the Yorkshire Vitality Suite dashboards looks incorrect, is missing, or appears not to have been updated.

---

## Step 1 - Check when the dataset was last loaded

Connect to the database (see [Query the database](../how-to/query-the-database.md)) and run:

```sql
SELECT dataset_code, extraction_status, rows_extracted, rows_loaded, loaded_at, error_message
FROM dataset_metadata
ORDER BY created_at DESC
LIMIT 30;
```

Look for the dataset in question and check:

- Was the most recent run a success or a failure?
- Does `rows_loaded` match `rows_extracted`? A mismatch suggests some rows were rejected.
- When was `loaded_at`? If it is several months ago, the flow may have stopped running.

---

## Step 2 - Check the indicator values directly

Run a query against the `indicator` table:

```sql
SELECT indicator_id, indicator_name, lad_name, reference_period, value, updated_at
FROM indicator
WHERE indicator_id = 'your_indicator_id'
ORDER BY reference_period DESC, lad_name;
```

Replace `your_indicator_id` with the relevant indicator (e.g. `employment_rate`, `life_expectancy_male`). This shows you exactly what is stored in the database.

---

## Step 3 - Compare with the source

If the value in the database does not match the source publication, the data may have been loaded incorrectly.

| Symptom | Likely cause |
|---------|--------------|
| Value is much older than expected | The flow has not run recently - check `dataset_metadata` |
| Value is present but obviously wrong | The source may have revised the figure - compare directly with the API or publication |
| Value is missing entirely | The row was not loaded - check the `rows_extracted` vs `rows_loaded` discrepancy |
| Dashboard shows no data | Power BI may be using a cached version - try refreshing the report |

---

## Step 4 - Re-run the flow

If the data is simply out of date, re-run the relevant flow manually. See [Re-run a flow manually](../how-to/re-run-a-flow.md).

After the flow completes, check `dataset_metadata` again to confirm `rows_loaded` is as expected, then refresh the Power BI report.

---
