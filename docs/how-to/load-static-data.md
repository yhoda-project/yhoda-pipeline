# Load a Static Dataset

Some indicators are not available through a live API and are instead sourced from preprocessed CSV files - for example, historical backfills or datasets still awaiting an API connector.
This guide explains how to load those files into the database manually.

---

## When you need this

Use this process when:

- You have a new preprocessed CSV for an existing indicator and want to backfill or update the database
- You are bootstrapping the database from scratch and need to load all historical data at once
- A live flow has not been built yet and you need to get data into the database now

---

## CSV format

The loader expects one of two formats.

**Wide format** (most common) — one row per LAD, one column per year:

| LAD_Name  | LAD_Code   | 2020 | 2021 | 2022 |
|-----------|------------|------|------|------|
| Bradford  | E08000032  | 72.1 | 73.4 | 74.0 |
| Leeds     | E08000035  | 75.2 | 76.1 | 76.8 |

Year column names can be plain years (`2022`) or date-range strings (`April 2021 to March 2022`) - the loader extracts the last 4-digit year automatically.

**Long format** - one row per LAD per year, with named columns for LAD code, LAD name, year, and value. Column names vary by dataset and are declared in `CSV_FILES` in `load_csv.py`.

Non-Yorkshire rows are filtered out automatically. Null values are dropped. Every load is an upsert - re-running the same file is safe and will not create duplicates.

---

## Step 1 — Find the dataset code

Every indicator has a short dataset code defined in `DATASET_REGISTRY` inside `src/yhovi_pipeline/utils/load_csv.py`. For example, `eejer` maps to employment rate.

If the indicator is not yet in `DATASET_REGISTRY`, add it following the existing pattern:

```python
"my_code": {
    "indicator_id": "my_indicator",
    "indicator_name": "Human-readable name",
    "unit": "%",
    "source": "ons",
    "subdomain": "Employment and Jobs",
},
```

---

## Step 2 — Place the file

Copy the CSV to the `data/` folder at the root of the repository. This folder is gitignored - files placed here are never committed.

```bash
cp /path/to/my_file.csv data/my_file.csv
```

---

## Step 3 — Load the file

Source your environment and run the loader from the VM:

```bash
export $(grep -v '^#' .env | xargs)
```

For a wide-format file:

```bash
uv run python - <<'EOF'
from yhovi_pipeline.utils.load_csv import load_dataset
load_dataset("data/my_file.csv", "eejer")
EOF
```

For a long-format file, pass the column names:

```bash
uv run python - <<'EOF'
from yhovi_pipeline.utils.load_csv import load_long_dataset
load_long_dataset(
    path="data/my_file.csv",
    dataset_code="ebebcr",
    lad_code_col="LAD23CD",
    lad_name_col="LocalAuthority",
    year_col="Year",
    value_col="ChurnRate_per_10000",
)
EOF
```

The output will report the number of rows upserted. If `0 rows upserted` is printed with no error, the most likely cause is that none of the LAD codes in the file matched Yorkshire codes - check the `LAD_Code` column.

---

## Load all historical data at once

To load the full set of preprocessed CSVs from the shared YHODA drive in one go:

```bash
export $(grep -v '^#' .env | xargs)
uv run python -m yhovi_pipeline.utils.load_csv
```

This runs `load_all()`, which iterates over every entry in `CSV_FILES` and `LONG_CSV_FILES` and reads from `BASE_PATH` (the shared drive at `/mnt/yhoda_drive/...`). It will print a summary line per dataset and a total at the end. Errors for individual datasets are caught and printed without stopping the rest of the load.

---

## Verifying the load

Connect to the database (see [Query the database](query-the-database.md)) and run:

```sql
SELECT indicator_id, count(*), min(reference_period), max(reference_period)
FROM indicator
WHERE dataset_code = 'eejer'
GROUP BY indicator_id;
```

Replace `eejer` with your dataset code. You should see one row per indicator with the expected date range and a count matching the number of LAD-year combinations in your file.
