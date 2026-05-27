# World Cup 2026 Prediction Analytics Warehouse

Built for DataCamp's FIFA World Cup 2026 Prediction competition, this project turns competition files and external soccer data into a tested dbt analytics warehouse and reproducible prediction pipeline.

The goal is practical first: generate a valid baseline submission, then improve model quality with better features. The portfolio goal is to demonstrate analytics engineering work: raw ingestion, staging models, marts, dbt tests, feature tables, CI, and clear documentation.

## Competition Context

- Competition: [Predict the FIFA World Cup 2026](https://app.datacamp.com/learn/competitions/world-cup-prediction)
- Current workbook requirements: predict scores, total corners, total yellow cards, total red cards, group-stage winners, knockout matchups, knockout winners, and penalties for all 104 matches.
- Starter files shown in DataCamp:
  - `data/group_fixtures.csv`: 72 group stage matches
  - `data/knockout_slots.csv`: 32 knockout round slots
- Workbook checklist says to publish before June 10, 2026 at 09:00 UTC. Recheck the DataCamp page before final submission.

## Project Stack

- Python for ingestion, modeling, tournament simulation, and submission generation
- DuckDB as the local analytical database
- dbt-duckdb for staging, intermediate, mart, and feature models
- GitHub Actions for basic CI

## Repository Layout

```text
.
|-- data/
|   |-- raw/              # Competition CSVs and optional external sources
|   `-- processed/        # DuckDB database and generated submissions
|-- dbt_profiles/         # Local dbt profile for DuckDB
|-- dbt_world_cup/        # dbt project
|-- docs/                 # Notes and project documentation
|-- notebooks/            # DataCamp submission notebook draft
`-- src/                  # Python pipeline code
```

## Setup

```powershell
cd "E:\Dev\Competitions\FIFA World Cup 2026"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy the competition CSVs into `data/raw/`:

```text
data/raw/group_fixtures.csv
data/raw/knockout_slots.csv
```

See [docs/datacamp_data_access.md](docs/datacamp_data_access.md) for notes on finding those files in DataCamp DataLab.

## Run The Pipeline

Validate the expected raw files:

```powershell
python src/ingest.py
```

Build dbt models:

```powershell
.\.venv\Scripts\dbt.exe build --project-dir dbt_world_cup --profiles-dir dbt_profiles
```

Generate first baseline prediction files:

```powershell
python src/generate_submission.py
```

The workbook-facing baseline outputs are written to:

```text
data/processed/group_predictions_baseline.csv
data/processed/knockout_predictions_baseline.csv
```

The combined analysis output is written to:

```text
data/processed/baseline_predictions.csv
```

## Learning Notes

Start with [docs/dbt_learning_notes.md](docs/dbt_learning_notes.md) for a walkthrough of the current dbt layers and why each one exists.

Use [docs/competition_submission_format.md](docs/competition_submission_format.md) to compare the local baseline output with the DataCamp workbook fields.

## Current Status

This repo has a working first baseline milestone: raw DataCamp files validate, dbt builds the local DuckDB warehouse, dbt tests pass, and Python generates group and knockout prediction files matching the workbook fields.
