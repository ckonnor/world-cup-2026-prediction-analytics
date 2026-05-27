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

For the DataCamp workbook, load `model_group_predictions_v2.csv` into `group_predictions` and `model_knockout_predictions_v2.csv` into `knockout_predictions`.
