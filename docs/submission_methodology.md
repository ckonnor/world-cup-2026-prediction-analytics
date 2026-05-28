# Submission Methodology

This is the competition-facing model summary for the DataCamp workbook/report.

## Summary

The submission uses a reproducible dbt + Python pipeline. dbt builds clean, tested feature tables from the raw competition files and external soccer data. Python trains the predictive models, simulates the group and knockout stages, validates the final workbook shape, and exports DataCamp-ready CSVs.

Final submission files:

```text
data/processed/submission_group_predictions.csv
data/processed/submission_knockout_predictions.csv
data/processed/submission_predictions.csv
data/processed/submission_validation.json
```

## Data Sources

- DataCamp group fixtures and knockout slots.
- Historical international match results.
- FIFA men's ranking history and latest ranking snapshot.
- External international match/player aggregate features.
- Current published World Cup squad tables where available.
- International corners/cards event data.
- Club player discipline data for squad-level card risk.

## dbt Feature Engineering

dbt owns the analytics engineering layer:

- staging models clean raw files and preserve raw-vs-resolved team names
- intermediate models create team-match rows, rolling prior-form features, ranking joins, squad features, and event features
- mart models expose team strength, latest rankings, squad strength, and event profiles
- feature models expose historical training rows and 2026 scoring rows

The key design choice is point-in-time modeling: historical match features only use information available before each match. dbt tests cover row counts, uniqueness, required values, placeholder resolution, ranking coverage, event coverage, and leakage checks.

## Modeling

The model has four prediction layers:

1. Expected goals
   - Poisson regression predicts home and away expected goals from prior form, FIFA rankings, and Elo features.

2. Direct outcome
   - A histogram gradient boosting classifier predicts home/draw/away probabilities using dbt features plus external player aggregate and form signals.

3. Final scoreline
   - Python builds a Poisson score grid for plausible exact scores.
   - Each scoreline is blended with the direct outcome probability for that scoreline's result.
   - Tournament-focused calibration selected a `0.25` outcome blend weight and a `0.35` draw threshold.

4. Events
   - Corners and cards are predicted from dbt-built team event profiles.
   - Yellow and red cards blend team-level international rates with squad-player club discipline where players can be matched.

## Validation

The train/holdout split is time based:

- training: matches before `2022-01-01`
- holdout: matches from `2022-01-01` onward

Calibration uses a 2018-2021 tournament-focused slice: World Cups, continental championships, Nations League-style competitions, and qualifiers.

Current holdout metrics:

| Metric | Value |
| --- | ---: |
| Direct outcome accuracy | 61.7% |
| Blended scoreline outcome accuracy | 62.4% |
| Exact score accuracy | 14.7% |
| Average goals MAE | 0.907 |

The final submission export validates:

- 72 group-stage rows
- 32 knockout rows
- all match IDs from 1 through 104
- no nulls in workbook-facing columns
- integer scores/events
- valid winner labels
- group winners consistent with predicted scores
- knockout penalty flags consistent with tied predicted scores

## Workbook Loading Snippet

Use these two DataFrames in the DataCamp workbook:

```python
import pandas as pd

group_predictions = pd.read_csv("data/submission_group_predictions.csv")
knockout_predictions = pd.read_csv("data/submission_knockout_predictions.csv")

group_predictions.head(), knockout_predictions.head()
```

The final local validation file is:

```text
data/processed/submission_validation.json
```
