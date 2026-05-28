# Competition Submission Format

The DataCamp workbook uses two prediction DataFrames.

## Group Stage

Variable name in workbook:

```python
group_predictions
```

Prediction columns:

- `predicted_home_goals`
- `predicted_away_goals`
- `corners`
- `yellow_cards`
- `red_cards`
- `winning_team`

`winning_team` must be one of:

- `home`
- `away`
- `draw`

## Knockout Stage

Variable name in workbook:

```python
knockout_predictions
```

Prediction columns:

- `predicted_home_team`
- `predicted_away_team`
- `predicted_home_goals`
- `predicted_away_goals`
- `corners`
- `yellow_cards`
- `red_cards`
- `match_winner`
- `penalties`

`match_winner` must be one of:

- `home`
- `away`

`penalties` must be boolean:

- `True`
- `False`

## Local Baseline Outputs

Run:

```powershell
.\.venv\Scripts\python.exe src\generate_submission.py
```

Outputs:

```text
data/processed/group_predictions_baseline.csv
data/processed/knockout_predictions_baseline.csv
data/processed/baseline_predictions.csv
```

## Local Model Outputs

Run:

```powershell
.\.venv\Scripts\python.exe src\train_model.py
```

Outputs:

```text
data/processed/model_group_predictions_v2.csv
data/processed/model_knockout_predictions_v2.csv
data/processed/model_predictions_v2.csv
```

## Final Submission Export

Run this after `src\train_model.py`:

```powershell
.\.venv\Scripts\python.exe src\export_datacamp_submission.py
```

Outputs:

```text
data/processed/submission_group_predictions.csv
data/processed/submission_knockout_predictions.csv
data/processed/submission_predictions.csv
data/processed/submission_validation.json
```

For the DataCamp workbook, load `submission_group_predictions.csv` into `group_predictions` and `submission_knockout_predictions.csv` into `knockout_predictions`.
