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
python src/generate_submission.py
```

Outputs:

```text
data/processed/group_predictions_baseline.csv
data/processed/knockout_predictions_baseline.csv
data/processed/baseline_predictions.csv
```
