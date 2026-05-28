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

## 2026 World Cup Squad Tables

Source page:

- Wikipedia: `https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads`

Downloaded file:

- `data/raw/external/world_cup_2026_squads.csv`

Run:

```powershell
python src/download_squad_data.py
```

Important source-data notes:

- This page changes as federations publish final or preliminary squads.
- The downloader only captures teams that have an actual player table under their team heading. Teams that have not published squads yet are left out instead of borrowing the next team's table.
- dbt aggregates the player rows into `main_marts.mart_squad_strength`, which the Python model uses as a conservative post-model star-power adjustment.

## FIFA Men's World Rankings

Source pages and APIs:

- Official FIFA ranking page: `https://inside.fifa.com/fifa-world-ranking/men`
- Official FIFA current rankings API: `https://api.fifa.com/api/v3/rankings?gender=1&count=250&language=en`
- Historical ranking CSV: `https://github.com/Dato-Futbol/fifa-ranking`

Downloaded file:

- `data/raw/external/fifa_rankings.csv`

Run:

```powershell
python src/download_fifa_rankings.py
```

How the data is used:

- dbt stages rankings in `main_staging.stg_fifa_rankings`.
- `main_intermediate.int_historical_match_rankings` joins the latest ranking available before each historical match.
- `main_marts.mart_latest_fifa_rankings` gives the 2026 prediction model the latest ranking snapshot for every World Cup team.

Important source-data notes:

- FIFA ranking data begins in 1992, so model training rows before that period are excluded once ranking features are required.
- The current ranking snapshot comes directly from FIFA's public API. Historical rows come from the Dato-Futbol scrape of FIFA's historical ranking pages, with recent FIFA ranking-window API rows layered in where available.
- The latest ranking date currently loaded is April 1, 2026.

## External Match And Player Features

Source page:

- Kaggle match-feature dataset: `https://www.kaggle.com/datasets/lchikry/international-football-match-features-and-statistics`

Downloaded files:

- `data/raw/external/international_match_features.csv`
- `data/raw/external/international_player_aggregates.csv`

Run:

```powershell
python src/download_match_feature_data.py
```

How the data is used:

- dbt stages historical match-level Elo, form, and player aggregate fields in `main_staging.stg_international_match_features`.
- dbt stages country-level player aggregate ratings by EA Sports/FIFA game version in `main_staging.stg_international_player_aggregates`.
- `main_marts.mart_external_player_strength` keeps the latest player aggregate snapshot per country for 2026 scoring.
- Python uses these columns only in the direct outcome model, not the goal model. That keeps goal MAE comparable while giving the winner-picking layer stronger team-quality signals.

Important source-data notes:

- The player aggregate features are EA Sports/FIFA-style country aggregates, not official national-team squad lists.
- Historical external features are not available for every project training row. Missing rows use training-set medians, and the model includes a `has_external_match_features` indicator.
- The latest player aggregate version in the downloaded data is FIFA 24, so this is a strong proxy signal rather than a perfect current-squad measure.

## Corners And Cards Event Data

Source pages:

- FootyStats CSV downloads: `https://footystats.org/download-stats-csv`
- FootyStats Premier League dataset example: `https://footystats.org/england/premier-league/datasets`
- Kaggle player stats dataset: `https://www.kaggle.com/datasets/hubertsidorowicz/football-players-stats-2025-2026`

Downloaded files:

- `data/raw/external/footystats_match_stats.csv`
- `data/raw/external/club_player_stats_2025_2026.csv`

Run:

```powershell
python src/download_event_data.py
```

How the data is used:

- FootyStats match CSVs provide team-level corners, yellow cards, and red cards for 2026 World Cup qualifying plus recent World Cups.
- The KaggleHub player file provides 2025/26 top-five-European-league player cards, fouls, minutes, and clubs. dbt joins these rows to the World Cup squad table by normalized player name plus country code.
- `main_marts.mart_team_event_profile` blends international team rates with club player discipline coverage. Corners stay team-level; card risk uses player-level club data when matched squad players are available.

Important source-data notes:

- Current FootyStats club player CSVs redirect to Premium, so the free automated pipeline uses KaggleHub for current club player discipline.
- Top-five-league player data helps with star-card-risk for elite squads but has weaker coverage for teams whose players are mostly outside those leagues.
- Red cards are rare, so the current model remains conservative and predicts zero red cards unless the blended expected rate becomes very high.

## Fixture Team Resolution

The DataCamp group fixture file was created before all playoff winners were known, so it can contain placeholders such as `UEFA Playoff A` and `FIFA Playoff 1`.

This project keeps the raw file unchanged and resolves those names in dbt with:

```text
dbt_world_cup/seeds/team_name_resolution.csv
```

The seed stores the raw fixture value, the display team name used in prediction outputs, and the model team name used to join against historical results.
