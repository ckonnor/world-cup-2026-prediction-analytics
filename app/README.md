# Streamlit Dashboard

This folder contains the portfolio dashboard app for the World Cup prediction project.

The app reads committed CSV snapshots from `app/data/`. Those files are generated from the dbt BI layer and final prediction outputs, then copied here so the dashboard can run on Streamlit Community Cloud without rebuilding the entire modeling pipeline.

Local run command:

```powershell
streamlit run app/streamlit_app.py
```

The app is intended to be hosted publicly after connecting the GitHub repository to Streamlit Community Cloud.
