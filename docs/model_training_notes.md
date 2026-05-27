# Model Training Notes

The current trained model is version 2 of the scoring pipeline. It is still intentionally explainable, but it is stronger than the first pass because it combines dbt-built form features with a Python-computed Elo rating system.

## How dbt Fits In

dbt is responsible for preparing clean, tested analytics tables:

- `main_features.features_historical_match_training`: one historical match per row, with prior-form features and target scores.
- `main_marts.mart_team_strength`: one row per team, with recent form as of the 2026 tournament start.
- `main_staging.stg_group_fixtures`: the 72 known group matches.
- `main_staging.stg_knockout_slots`: the 32 bracket slots.
- `main_staging.stg_international_results`: historical results used by the Python Elo pass.

Python then reads those dbt outputs from DuckDB. This is the usual analytics engineering pattern: dbt owns reproducible feature preparation, while Python owns model training and prediction logic.

## Model

Run:

```powershell
.\.venv\Scripts\python.exe src\train_model.py
```

The script trains separate home-goal and away-goal models. It compares two candidate model families:

- Poisson regression with scaled numeric features.
- Histogram gradient boosting with Poisson loss.

The selected model is the candidate with the lowest holdout average goal MAE.

## Features

The model uses:

- prior-10-match points, goal difference, goals for, and goals against for both teams
- home minus away differences for those prior-form features
- neutral-site flag, including host advantage for Canada, Mexico, and the United States
- pre-match Elo rating for both teams
- Elo difference and the Elo expected home result

Small team-name aliases connect fixture names such as `USA`, `Cabo Verde`, and `Cote d'Ivoire` to the historical source names.

## Evaluation

The train/holdout split is time-based:

- Training rows: matches before `2022-01-01`
- Holdout rows: matches from `2022-01-01` onward

Current v2 holdout metrics:

```text
Selected model: poisson_regression
Holdout rows: 4,400
Holdout home goals MAE: 1.027
Holdout away goals MAE: 0.840
Holdout average goals MAE: 0.934
Holdout rounded exact score accuracy: 0.103
Holdout rounded match outcome accuracy: 0.561
```

For comparison, v1 had holdout match outcome accuracy of about `0.482`, so the Elo features are a meaningful improvement.

## Outputs

The model writes:

```text
data/processed/model_group_predictions_v2.csv
data/processed/model_knockout_predictions_v2.csv
data/processed/model_predictions_v2.csv
data/processed/model_metrics_v2.json
```

`model_group_predictions_v2.csv` and `model_knockout_predictions_v2.csv` match the two DataCamp workbook sections. `model_predictions_v2.csv` combines all 104 matches for local analysis.

## Known Limitations

- Corners and cards are still constants because the current historical source does not contain corners or card data.
- Playoff placeholders still need real teams once those qualifiers are known.
- Knockout scores use the same goal model, then resolve tied rounded scorelines as penalty matches.
- This is a strong first modeling baseline, not a final betting-grade forecast.
