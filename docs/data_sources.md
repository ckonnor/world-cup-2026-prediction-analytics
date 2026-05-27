# Data Sources

## DataCamp Competition Files

Local files:

- `data/raw/group_fixtures.csv`
- `data/raw/knockout_slots.csv`

These files come from the DataCamp competition workbook and are not committed to Git.

## Historical International Results

Dataset page:

- Kaggle: `https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017`

Reproducible raw source used by this project:

- GitHub: `https://github.com/martj42/international_results`

Downloaded files:

- `results.csv`
- `shootouts.csv`

Known source-data note:

- The current `shootouts.csv` contains one shootout that does not map to `results.csv`: Saare County vs. Åland Islands on 2011-06-29. The dbt data test allows this one known mismatch and fails if additional unmatched shootout rows appear.

Why use GitHub raw URLs instead of Kaggle for the automated pipeline?

- No Kaggle API credentials are required.
- The URLs can be used directly from a Python script and dbt/DuckDB.
- The same dataset remains easy to cite through Kaggle and GitHub.

Run:

```powershell
python src/download_external_data.py
```

## Fixture Team Resolution

The DataCamp group fixture file was created before all playoff winners were known, so it can contain placeholders such as `UEFA Playoff A` and `FIFA Playoff 1`.

This project keeps the raw file unchanged and resolves those names in dbt with:

```text
dbt_world_cup/seeds/team_name_resolution.csv
```

The seed stores the raw fixture value, the display team name used in prediction outputs, and the model team name used to join against historical results.
