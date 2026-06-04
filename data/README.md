# data/

This folder is a local staging area for static-release CSV files that need loading into the database.

Data files are excluded from version control (see `.gitignore`). Only this README and `.gitkeep` are committed.

## When to use this folder

Drop a preprocessed CSV here when you need to load a single dataset manually - for example, a historical backfill or a one-off update for a dataset that is not yet on a live API feed.

## How to load a file

See [Load a static dataset](https://yhoda-project.github.io/yhoda-pipeline/how-to/load-static-data/) in the documentation for full instructions.

In short:

```bash
# On the VM, with your .env sourced
uv run python - <<'EOF'
from yhovi_pipeline.utils.load_csv import load_dataset
load_dataset("data/my_file.csv", "eejer")
EOF
```

Replace `my_file.csv` with your filename and `eejer` with the correct dataset code from `DATASET_REGISTRY` in `src/yhovi_pipeline/utils/load_csv.py`.
