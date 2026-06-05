# Add a New Dataset

This guide walks through the steps to add a new data source to the pipeline. It is written for someone who is comfortable editing Python files but may not have built a Prefect pipeline before.

The steps follow the same pattern as every existing data source. If you get stuck, look at the NOMIS extract task (`src/yhovi_pipeline/tasks/extract/nomis.py`) and the earnings flow (`src/yhovi_pipeline/flows/economy/earnings.py`) as working examples.

---

## Before you start

You will need:

- A working understanding of the new data source - what it provides, how to request data from it, and what format it returns
- Access to the GitHub repository and the ability to run the pipeline on the staging VM
- The indicator ID and name you want to use for the new dataset

---

## Step 1 - Write an extract task

Create a new file (or add a function) in `src/yhovi_pipeline/tasks/extract/`. Name it after the data source, e.g. `my_source.py`.

The extract task is responsible for connecting to the source and returning the raw data as a pandas DataFrame. Keep it small - its only job is to fetch. Leave validation and reshaping for the transform step.

Decorate it with:

```python
@task(name="extract/<source>/<action>", retries=3, retry_delay_seconds=60)
```

The `retries=3` means Prefect will automatically retry the task up to three times if it fails - useful for handling temporary API outages without the whole flow failing.

---

## Step 2 - Add a normaliser if needed

Open `src/yhovi_pipeline/tasks/transform/normalise.py`.

If the new source uses a non-standard date format or a different column layout, add a normaliser function here. If the source returns data in the same format as an existing one, you may be able to reuse an existing normaliser.

The normaliser's job is to reshape whatever the source returns into the standard format the `indicator` table expects.

---

## Step 3 - Create a flow

Create a new file in the appropriate domain directory:

- `src/yhovi_pipeline/flows/economy/` for economic indicators
- `src/yhovi_pipeline/flows/society/` for social indicators
- `src/yhovi_pipeline/flows/environment/` for environmental indicators

The flow orchestrates the three stages: extract → transform → load. Use this decorator pattern:

```python
@flow(
    name="economy/my-dataset",
    flow_run_name=lambda **_: datetime.now().strftime("%B %Y") + " - Economy: My Dataset",
    retries=1,
    retry_delay_seconds=300,
    task_runner=ThreadPoolTaskRunner(max_workers=4),
)
```

The `flow_run_name` lambda generates a human-readable label in the Prefect UI (e.g. "June 2026 - Economy: My Dataset"), making it easy for non-technical stakeholders to identify runs.

Inside the flow:

1. Call your extract task
2. Call validate and normalise tasks
3. Call `upsert_indicators` to load to the database
4. Call `write_metadata` to log the run
5. Call `create_table_artifact` with a load summary at the end

Wrap the body in a `try/finally` block so the artifact is always emitted even if the flow fails partway through.

---

## Step 4 - Register the deployment

Open `prefect.yaml` and add an entry for your new flow following the existing pattern:

```yaml
- name: economy-my-dataset
  entrypoint: src/yhovi_pipeline/flows/economy/my_dataset.py:my_dataset_flow
  tags: ["economy"]
  <<: *common
```

The `<<: *common` line applies the shared monthly schedule and work pool automatically - you do not need to configure these separately.

After editing `prefect.yaml`, re-register all deployments:

```bash
uv run prefect deploy --all --no-prompt
```

---

## Step 5 - Add the indicator to the dataset registry

Open `src/yhovi_pipeline/utils/load_csv.py` and add the new indicator(s) to the `DATASET_REGISTRY` dictionary. This is needed if the dataset will ever be loaded from a CSV file (e.g. for a historical backfill before the live API feed begins).

---

## Step 6 - Write unit tests

Add a test file in `tests/unit/` covering your transform logic. Tests for the extract task itself are typically not needed - the task is just an HTTP call, and bugs almost always live in the transform step.

Run the tests before opening a pull request:

```bash
uv run pytest tests/unit/
```

---

## Step 7 - Open a pull request

Push your branch and open a pull request on GitHub. The CI pipeline will run the linter and tests automatically. Once it passes and a team member has reviewed it, merge to `main` - the Prefect deployment will update automatically.
