# Operations and Deployment

This project has two operating modes:

- a full local build, used when raw data files and the DuckDB warehouse are available
- a lightweight hosted dashboard, used for portfolio sharing

## Full Local Refresh

The local refresh rebuilds the warehouse, retrains the model, validates the competition submission, and regenerates dashboard extracts.

```powershell
.\.venv\Scripts\dbt.exe build --project-dir dbt_world_cup --profiles-dir dbt_profiles
.\.venv\Scripts\python.exe src\train_model.py
.\.venv\Scripts\python.exe src\export_datacamp_submission.py
.\.venv\Scripts\python.exe src\export_bi_assets.py
```

After the BI exports are refreshed, copy the generated dashboard CSVs from `data/bi_exports/` into `app/data/` before committing the hosted snapshot.

## CI Gates

GitHub Actions validates the public repo state on every push and pull request:

- installs the pinned Python/dbt environment
- parses the dbt project graph
- runs a full dbt build only when raw files are present
- compiles Python, tests, and the Streamlit app
- runs Python tests and dashboard snapshot contracts
- uploads dbt parse artifacts for lineage inspection

The raw source files are intentionally not committed, so CI is designed to distinguish between public validation and full local rebuilds.

## Dashboard Deployment

The dashboard app is designed for Streamlit Community Cloud:

- app entrypoint: `app/streamlit_app.py`
- dependency file: `requirements.txt`
- app data snapshot: `app/data/`
- theme config: `.streamlit/config.toml`

Once the GitHub repository is connected in Streamlit Community Cloud, the app can deploy from the `main` branch without access to the local DuckDB warehouse.

## Deployment Readiness Checklist

- CI passing on `main`
- `app/data/` contains the latest dashboard snapshot
- `app/streamlit_app.py` runs locally
- README links to the deployed app once available
- dashboard tabs render without traceback or missing snapshot files

## Refresh Cadence

For a competition project, refreshes should happen only when one of these changes:

- raw competition fixtures are updated
- new FIFA ranking data is added
- squad/player source quality improves
- modeling logic changes
- dashboard table contracts change

That keeps the public dashboard stable while preserving a repeatable path for future updates.
