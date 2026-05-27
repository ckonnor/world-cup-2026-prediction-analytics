# Model Training Notes

The first trained model is intentionally simple and explainable.

## Inputs

The training script reads from DuckDB tables built by dbt:

- `main_features.features_historical_match_training`
- `main_features.features_world_cup_group_matches`

This keeps the model connected to tested dbt transformations instead of reading raw CSV files directly.

## Model

The first version trains two separate scikit-learn pipelines:

- one `PoissonRegressor` for home goals
- one `PoissonRegressor` for away goals

Poisson regression is a reasonable first pass because soccer goals are non-negative count outcomes.

## Evaluation

The train/holdout split is time-based:

- Training rows: matches before `2022-01-01`
- Holdout rows: matches from `2022-01-01` onward

Metrics are written to:

```text
data/processed/model_metrics_v1.json
```

## Outputs

Run:

```powershell
python src/train_model.py
```

Output:

```text
data/processed/model_group_predictions_v1.csv
```

This file matches the group-stage prediction columns expected by the DataCamp workbook.

## Known Limitations

- Corners and cards are still constants because the current historical source does not contain corners/card data.
- Knockout predictions still use the earlier baseline bracket flow.
- Some 2026 fixture rows involve playoff placeholders or team-name mismatches, so missing team-strength features are filled with training-set median values.
