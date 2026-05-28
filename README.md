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
|   |-- bi_exports/       # Reproducible dashboard CSV extracts
|   `-- processed/        # DuckDB database and generated submissions
|-- dbt_profiles/         # Local dbt profile for DuckDB
|-- dbt_world_cup/        # dbt project
|   `-- seeds/            # Small manual lookup tables used by dbt
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

Download historical international results:

```powershell
python src/download_external_data.py
```

Download currently published World Cup squad tables:

```powershell
python src/download_squad_data.py
```

Download event data for corners and cards:

```powershell
python src/download_event_data.py
```

Download FIFA ranking history and the latest official FIFA ranking snapshot:

```powershell
python src/download_fifa_rankings.py
```

Download external international match/player features:

```powershell
python src/download_match_feature_data.py
```

See [docs/data_sources.md](docs/data_sources.md) for source details.

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

Train the model-driven scorer:

```powershell
.\.venv\Scripts\python.exe src\train_model.py
```

Export and validate the final DataCamp-ready submission tables:

```powershell
.\.venv\Scripts\python.exe src\export_datacamp_submission.py
```

Export dashboard-ready CSV assets:

```powershell
.\.venv\Scripts\python.exe src\export_bi_assets.py
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

The current model-driven outputs are written to:

```text
data/processed/model_group_predictions_v2.csv
data/processed/model_knockout_predictions_v2.csv
data/processed/model_predictions_v2.csv
data/processed/model_metrics_v2.json
data/processed/submission_group_predictions.csv
data/processed/submission_knockout_predictions.csv
data/processed/submission_predictions.csv
data/processed/submission_validation.json
```

The BI/dashboard exports are written to:

```text
data/bi_exports/dashboard_match_predictions.csv
data/bi_exports/dashboard_group_standings.csv
data/bi_exports/dashboard_team_profiles.csv
data/bi_exports/dashboard_match_feature_context.csv
data/bi_exports/dashboard_model_metrics.csv
data/bi_exports/dashboard_data_quality.csv
data/bi_exports/dashboard_historical_competition_summary.csv
```

## Learning Notes

Start with [docs/dbt_learning_notes.md](docs/dbt_learning_notes.md) for a walkthrough of the current dbt layers and why each one exists.

Use [docs/competition_submission_format.md](docs/competition_submission_format.md) to compare the local baseline output with the DataCamp workbook fields.

Use [docs/exploring_the_project.md](docs/exploring_the_project.md) for a hands-on guide to browsing dbt docs, reading models, and querying the DuckDB warehouse.

Use [docs/model_training_notes.md](docs/model_training_notes.md) for notes on the trained model and how dbt feeds the Python modeling step.

Use [docs/tournament_realism_review.md](docs/tournament_realism_review.md) for the latest full-tournament sanity check of group standings, tiebreaks, and the knockout bracket.

Use [docs/submission_methodology.md](docs/submission_methodology.md) for a competition-facing model summary and workbook loading snippet.

Use [docs/dashboard_guide.md](docs/dashboard_guide.md) for the Looker Studio/dashboard build plan and BI export definitions.

Use [docs/resume_project_positioning.md](docs/resume_project_positioning.md) for a concise analytics engineering resume framing.

## Current Status

This repo has a working baseline plus a v2 model: raw DataCamp files validate, external international results, FIFA ranking history, external match/player aggregate features, currently published squad tables, FootyStats match events, and KaggleHub club player stats download reproducibly. dbt resolves stale playoff placeholders through a tested seed, builds the local DuckDB warehouse, tests the transformation assumptions, and Python generates group and knockout prediction files matching the workbook fields. The current model adds Elo, FIFA ranking, and external player aggregate features to dbt-built recent-form features, applies a conservative squad star-power overlay, predicts corners/cards from the dbt-built team event profile, and selects final scorelines with a tournament-calibrated blend of Poisson score probabilities and direct outcome probabilities. The project also includes a dashboard-ready BI layer and reproducible CSV extracts for Looker Studio or another visualization tool.
