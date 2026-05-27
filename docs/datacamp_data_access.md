# DataCamp Data Access Notes

The competition notebook shown in DataCamp references:

- `data/group_fixtures.csv`
- `data/knockout_slots.csv`

If `pd.read_csv("data/group_fixtures.csv")` raises `FileNotFoundError` inside DataLab, check the right sidebar:

1. Open the `FILES` tab, not only `DATA SOURCES`.
2. Look for a `data/` folder in the workbook file tree.
3. If the folder exists, use the file menu to download the CSVs.
4. If the folder does not exist, create a cell and run:

```python
import os
for root, _, files in os.walk("."):
    for file in files:
        print(os.path.join(root, file))
```

Copy the downloaded files into this local project:

```text
E:\Dev\Competitions\FIFA World Cup 2026\data\raw\group_fixtures.csv
E:\Dev\Competitions\FIFA World Cup 2026\data\raw\knockout_slots.csv
```

Once those files are local, run:

```powershell
python src/ingest.py
```
