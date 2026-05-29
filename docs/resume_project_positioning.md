# Resume Project Positioning

Use this project as an analytics engineering portfolio case study, not only a machine-learning competition entry.

## Suggested Resume Bullet

Built a reproducible FIFA World Cup 2026 forecasting warehouse using Python, DuckDB, and dbt, integrating competition fixtures, historical international results, FIFA rankings, squad/player data, corners/cards event data, and external player-strength features; published tested marts, model-ready feature tables, BI extracts, and validated prediction outputs for 104 tournament matches.

## What This Demonstrates

- Analytics engineering: layered dbt project with staging, intermediate, marts, features, and BI models.
- Data modeling: fact/dimension-style schedule and team profile tables.
- Data quality: dbt tests for row counts, uniqueness, accepted values, placeholder resolution, feature coverage, and leakage prevention.
- Feature engineering: point-in-time rolling form, FIFA ranking joins, international pedigree, event profiles, and player-strength proxies.
- Python orchestration: model training, calibration, tournament simulation, knockout bracket resolution, and export validation.
- BI readiness: dashboard-specific marts and CSV extracts for Looker Studio or another visualization tool.

## Project Talking Points

- dbt owns repeatable SQL transformations and tests; Python owns model training and stateful knockout simulation.
- Historical features are point-in-time to avoid future-data leakage.
- Playoff placeholder teams are resolved through a tested seed while preserving raw source names.
- Final submission files are schema-validated before use in DataCamp.
- The BI layer separates dashboard consumption tables from model-training tables, which mirrors real analytics engineering practice.

## Next Portfolio Improvements

- Deploy the Streamlit dashboard and add the public app link to the README.
- Add dbt docs screenshots for the feature and BI model lineage.
- Add dashboard screenshots to the repo page once the final visual state is stable.
- Write a short case-study post that explains the project decisions in business language.
