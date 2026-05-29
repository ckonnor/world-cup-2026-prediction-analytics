# BI Exports

This folder is the local output target for dashboard-ready CSV files created by:

```powershell
.\.venv\Scripts\python.exe src\export_bi_assets.py
```

The generated CSV files are ignored by git because they are reproducible from the dbt warehouse and model outputs.

The hosted dashboard snapshot in `app/data/` is copied from this folder after refreshes, including the tournament simulation probability table.
