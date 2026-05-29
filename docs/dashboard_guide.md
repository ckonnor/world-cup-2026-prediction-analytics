# Dashboard Guide

This project now has a BI-ready layer and a Streamlit dashboard for a resume-friendly analytics engineering story.

## Dashboard Goal

The dashboard should answer four questions:

1. Which teams does the model expect to advance or win the title?
2. Why are certain teams favored?
3. Where are the highest-risk or most interesting matches?
4. How reliable and complete is the data feeding the forecast?

## Build The BI Assets

Run the full local pipeline:

```powershell
.\.venv\Scripts\dbt.exe build --project-dir dbt_world_cup --profiles-dir dbt_profiles
.\.venv\Scripts\python.exe src\train_model.py
.\.venv\Scripts\python.exe src\export_datacamp_submission.py
.\.venv\Scripts\python.exe src\export_bi_assets.py
```

The dashboard CSVs are written to:

```text
data/bi_exports/
```

## BI Export Files

| File | Grain | Purpose |
| --- | --- | --- |
| `dashboard_match_predictions.csv` | One row per match | Final group and knockout predictions for score, winner, corners, cards, and penalties |
| `dashboard_group_standings.csv` | One row per team per group | Predicted group table with rank, points, goals, and goal difference |
| `dashboard_team_profiles.csv` | One row per team | Team Elo, opponent-adjusted form, FIFA ranking, squad strength, event profile, external player rating context, and star-power index |
| `dashboard_player_power_profiles.csv` | One row per squad player | Roster star-power proxy using post-2022-World-Cup top-league form, league-adjusted goal contribution per 90, market value, and squad caps/goals context |
| `dashboard_match_feature_context.csv` | One row per group match | Pre-match feature differences used to explain group-stage predictions |
| `dashboard_model_metrics.csv` | One row per model metric | Guardrail, target, stretch, and current model performance |
| `dashboard_data_quality.csv` | One row per validation check | Submission row counts and prediction distribution checks |
| `dashboard_historical_competition_summary.csv` | One row per year/tournament | Training-data coverage and historical scoring environment |
| `dashboard_tournament_simulation.csv` | One row per team | Advancement, title probability, and route difficulty from repeated full-tournament simulations |

## Streamlit Path

The fastest portfolio dashboard is the Streamlit app in:

```text
app/streamlit_app.py
```

It reads the committed snapshot in:

```text
app/data/
```

That snapshot is copied from the reproducible BI exports so the hosted dashboard can run without raw files, the local DuckDB warehouse, or a long rebuild.

Suggested hosting path:

1. Open [Streamlit Community Cloud](https://streamlit.io/cloud).
2. Connect the GitHub repository.
3. Use `app/streamlit_app.py` as the main app file.
4. Deploy from the `main` branch.
5. Add the public app URL to the README.

## Looker Studio Path

Looker Studio is a good free presentation layer, but the local DuckDB file is not the cleanest direct input. Use CSV upload or Google Sheets as the bridge:

1. Open [Looker Studio](https://lookerstudio.google.com/).
2. Create a blank report.
3. Add each dashboard CSV as a data source through file upload, or upload the CSVs to Google Sheets and connect those sheets.
4. Keep `dashboard_match_predictions.csv` as the main report-level data source.
5. Add the other sources only on pages that need them.

## Streamlit Dashboard Pages

The current Streamlit dashboard is organized into four stakeholder-facing pages.

| Page | Purpose | Primary Sources |
| --- | --- | --- |
| Overview | Lead with the deterministic forecast, validation metrics, championship probabilities, project story, dbt usage, and scoring environment. | `dashboard_match_predictions.csv`, `dashboard_model_metrics.csv`, `dashboard_team_profiles.csv`, `dashboard_tournament_simulation.csv`, `dashboard_historical_competition_summary.csv` |
| Tournament | Show the deterministic bracket, group standings, fixtures, match cards, and feature context. | `dashboard_match_predictions.csv`, `dashboard_group_standings.csv`, `dashboard_match_feature_context.csv` |
| Teams | Compare the field or inspect one selected team across strength signals, route difficulty, and predicted path. | `dashboard_team_profiles.csv`, `dashboard_tournament_simulation.csv`, `dashboard_match_predictions.csv` |
| Methodology | Connect forecast outputs back to validation targets, modeling choices, data quality, and source links. | `dashboard_model_metrics.csv`, `dashboard_data_quality.csv`, `dashboard_historical_competition_summary.csv` |

## Portfolio Framing

The dashboard is the final consumption layer. The resume story should emphasize the full analytics workflow:

- raw data ingestion from multiple soccer sources
- dbt staging, intermediate, mart, feature, and BI layers
- data tests for row counts, uniqueness, coverage, and leakage prevention
- Python model training and tournament simulation
- validated competition submission exports
- BI-ready dashboard extracts
