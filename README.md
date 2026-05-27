# World Cup 2026 Prediction Analytics Warehouse

Built for DataCamp's FIFA World Cup 2026 Prediction competition, this project turns competition files and external soccer data into a tested dbt analytics warehouse and reproducible prediction pipeline.

The goal is practical first: generate a valid baseline submission, then improve model quality with better features. The portfolio goal is to demonstrate analytics engineering work: raw ingestion, staging models, marts, dbt tests, feature tables, CI, and clear documentation.

## Competition Context

- Competition: [Predict the FIFA World Cup 2026](https://app.datacamp.com/learn/competitions/world-cup-prediction)
- Current visible requirements: predict scores, corners, cards, and knockout outcomes for all 104 matches.
- Starter files shown in DataCamp:
  - `data/group_fixtures.csv`: 72 group stage matches
  - `data/knockout_slots.csv`: 32 knockout round slots
- Deadline shown publicly: June 11, 2026 at 09:00 UTC.

## Project Stack

- Python for ingestion, modeling, tournament simulation, and submission generation
- DuckDB as the local analytical database
- dbt-duckdb for staging, intermediate, mart, and feature models
- GitHub Actions for basic CI

## Repository Layout

```text
.
├── data/
│   ├── raw/              # Competition CSVs and optional external sources
│   └── processed/        # DuckDB database and generated submissions
├── dbt_profiles/         # Local dbt profile for DuckDB
├── dbt_world_cup/        # dbt project
├── docs/                 # Notes and project documentation
├── notebooks/            # DataCamp submission notebook draft
└── src/                  # Python pipeline code
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
cd dbt_world_cup
dbt build --profiles-dir ..\dbt_profiles
cd ..
```

Generate a first baseline prediction file:

```powershell
python src/generate_submission.py
```

The baseline output is written to:

```text
data/processed/baseline_predictions.csv
```

## Current Status

This repo is scaffolded for the first baseline milestone. The next step is to copy or export the two DataCamp CSV files, run the ingestion check, and inspect the exact submission format from DataCamp before finalizing the submission writer.
