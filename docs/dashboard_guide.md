# Dashboard Guide

This project now has a BI-ready layer for a resume-friendly analytics engineering story.

## Dashboard Goal

The dashboard should answer four questions:

1. Which teams does the model expect to advance?
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
| `dashboard_team_profiles.csv` | One row per team | Team form, FIFA ranking, squad strength, event profile, and external player rating context |
| `dashboard_match_feature_context.csv` | One row per group match | Pre-match feature differences used to explain group-stage predictions |
| `dashboard_model_metrics.csv` | One row per model metric | Guardrail, target, stretch, and current model performance |
| `dashboard_data_quality.csv` | One row per validation check | Submission row counts and prediction distribution checks |
| `dashboard_historical_competition_summary.csv` | One row per year/tournament | Training-data coverage and historical scoring environment |

## Looker Studio Path

Looker Studio is a good free presentation layer, but the local DuckDB file is not the cleanest direct input. Use CSV upload or Google Sheets as the bridge:

1. Open [Looker Studio](https://lookerstudio.google.com/).
2. Create a blank report.
3. Add each dashboard CSV as a data source through file upload, or upload the CSVs to Google Sheets and connect those sheets.
4. Keep `dashboard_match_predictions.csv` as the main report-level data source.
5. Add the other sources only on pages that need them.

## Suggested Pages

### Tournament Overview

- Scorecards: champion, runner-up, total predicted goals, predicted penalty shootouts.
- Bar chart: matches by result label.
- Table: final four and final match.
- Filter controls: phase, round, group.

Primary source: `dashboard_match_predictions.csv`.

### Group Stage

- Group table by `group_letter` and `group_rank`.
- Scoreline table by match.
- Bar chart: points by team within selected group.

Primary sources:

- `dashboard_group_standings.csv`
- `dashboard_match_predictions.csv`

### Team Strength

- Scatter plot: FIFA rank vs overall star power.
- Bar chart: last-10 points per match by team.
- Table: profile completeness and data coverage flags.

Primary source: `dashboard_team_profiles.csv`.

### Match Context

- Table: group matches with FIFA rank difference, form difference, star-power difference, and expected cards/corners.
- Conditional formatting: highlight large rank or star-power differences.

Primary source: `dashboard_match_feature_context.csv`.

### Model Quality

- Scorecards: direct outcome accuracy, blended outcome accuracy, exact score accuracy, average goals MAE.
- Bullet/table visual: current vs guardrail/target/stretch.
- Data quality checks: row counts and prediction distributions.

Primary sources:

- `dashboard_model_metrics.csv`
- `dashboard_data_quality.csv`

## Portfolio Framing

The dashboard is the final consumption layer. The resume story should emphasize the full analytics workflow:

- raw data ingestion from multiple soccer sources
- dbt staging, intermediate, mart, feature, and BI layers
- data tests for row counts, uniqueness, coverage, and leakage prevention
- Python model training and tournament simulation
- validated competition submission exports
- BI-ready dashboard extracts
