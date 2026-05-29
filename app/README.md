# Streamlit Dashboard

This folder contains the portfolio dashboard app for the World Cup prediction project.

The dashboard is designed as the public presentation layer: it explains the forecast, bracket, team profiles, match predictions, and model evidence without requiring access to raw files or the local DuckDB warehouse.

The app reads committed CSV snapshots from `app/data/`. Those files are generated from the dbt BI layer and final prediction outputs, then copied here so the dashboard can run on Streamlit Community Cloud as a lightweight hosted artifact.

CI validates the dashboard code and the committed data snapshot through `tests/test_dashboard_assets.py`.
