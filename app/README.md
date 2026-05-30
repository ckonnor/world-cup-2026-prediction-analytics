# Streamlit Dashboard

This folder contains the portfolio dashboard app for the World Cup prediction project.

The dashboard is designed as the public presentation layer: it explains the forecast, bracket, championship probabilities, team profiles, match predictions, and model evidence without requiring access to raw files or the local DuckDB warehouse.

The app reads committed CSV snapshots from `app/data/`. Those files are generated from the dbt BI layer and final prediction outputs, then copied here so the dashboard can run on Streamlit Community Cloud as a lightweight hosted artifact.

The root `requirements.txt` and `app/requirements.txt` are intentionally kept small and dashboard-only. The full dbt/modeling toolchain lives in `requirements-dev.txt`, which keeps the hosted app from installing local-only packages such as dbt, DuckDB, PyArrow, and scikit-learn.

CI validates the dashboard code and the committed data snapshot through `tests/test_dashboard_assets.py`.
