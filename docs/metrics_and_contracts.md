# Metrics and Data Contracts

This project uses two kinds of contracts:

- model-performance contracts, which define how the forecast is evaluated
- data contracts, which define the grains and required fields used by dbt, Python, and the dashboard

## Model Metrics

| Metric | Definition | Direction | Why It Matters |
| --- | --- | --- | --- |
| Rounded scoreline outcome accuracy | Accuracy of the winner/draw implied by rounded goal predictions. | Higher is better | Checks whether the score model points to the right match result. |
| Direct outcome accuracy | Accuracy of the direct home/draw/away classifier. | Higher is better | Measures the high-signal outcome model independent of exact scoreline. |
| Blended outcome accuracy | Accuracy after reconciling scoreline and outcome probabilities. | Higher is better | Best summary metric for whether the final predicted score produces the right outcome. |
| Reconciled exact score accuracy | Exact scoreline accuracy after calibration. | Higher is better | Useful for the competition, but volatile and naturally lower than outcome accuracy. |
| Average goals MAE | Mean absolute error across home and away goals. | Lower is better | Measures scoreline distance even when exact score misses. |

Current targets are stored in `dashboard_model_metrics.csv` and shown in the Streamlit **Model Evidence** tab.

## Dashboard Data Contracts

The hosted dashboard reads CSV snapshots from `app/data/`. These are treated as public-facing BI contracts and are now validated by `tests/test_dashboard_assets.py`.

| File | Grain | Key Contract |
| --- | --- | --- |
| `dashboard_match_predictions.csv` | One row per tournament match | 104 rows, unique `match_id`, 72 group rows, 32 knockout rows, scoreline and winner fields populated. |
| `dashboard_group_standings.csv` | One row per team per group | 48 rows, one team per group entry, groups A through L present. |
| `dashboard_team_profiles.csv` | One row per team | 48 unique teams, ranking, Elo, adjusted-form, squad, event, and completeness fields present. |
| `dashboard_match_feature_context.csv` | One row per group-stage match | 72 rows of pre-match explanatory feature differences. |
| `dashboard_model_metrics.csv` | One row per model metric | Five tracked metrics with target, guardrail, stretch, and status. |
| `dashboard_data_quality.csv` | One row per validation check | Submission validity and row-count checks for group, knockout, and combined predictions. |
| `dashboard_historical_competition_summary.csv` | One row per historical tournament-year | Training-data context for scoring environment and coverage. |

## dbt Model Contracts

dbt schema files define model-level expectations for:

- uniqueness and non-null keys
- accepted values for categorical fields
- required feature columns
- row-count tests for fixture and BI models
- leakage prevention in historical training features
- playoff placeholder resolution

The most important contract is point-in-time feature integrity. Historical training rows must only use information available before the match date. That prevents future data from leaking into validation performance.

## Dashboard Contract Tests

The dashboard contract tests intentionally run without the raw source files. They protect the committed presentation snapshot, which is the artifact a recruiter or stakeholder will see first.

If the model is refreshed, the expected workflow is:

1. rebuild dbt locally with raw files
2. train and simulate the tournament
3. export BI assets
4. copy the refreshed CSVs into `app/data/`
5. run the Python and dashboard contract tests
