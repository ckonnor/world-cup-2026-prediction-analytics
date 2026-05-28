# Exploring The Project

Use this guide when you want to understand what has been built so far.

## 1. Start With The dbt Docs Site

Generate the docs:

```powershell
.\.venv\Scripts\dbt.exe docs generate --project-dir dbt_world_cup --profiles-dir dbt_profiles
```

Serve the docs locally:

```powershell
.\.venv\Scripts\dbt.exe docs serve --project-dir dbt_world_cup --profiles-dir dbt_profiles --port 8080
```

Open:

```text
http://localhost:8080
```

What to look for:

- The lineage graph: how raw-style staging models flow into intermediate models, marts, and features.
- Each model page: SQL, columns, tests, and downstream dependencies.
- Test coverage: `not_null`, `unique`, `accepted_values`, and custom SQL tests.

## 2. Read Models In This Order

### Staging

Folder:

```text
dbt_world_cup/models/staging/
```

Purpose:

- Read raw CSVs.
- Rename awkward columns.
- Cast types.
- Filter source records that do not belong in training data.

Start with:

- `stg_group_fixtures.sql`
- `stg_international_results.sql`
- `stg_fifa_rankings.sql`
- `stg_footystats_match_stats.sql`
- `stg_club_player_stats.sql`

### Intermediate

Folder:

```text
dbt_world_cup/models/intermediate/
```

Purpose:

- Reshape data into reusable business concepts.
- Avoid duplicating logic in final tables.

Start with:

- `int_historical_team_match_results.sql`
- `int_team_form_rolling.sql`
- `int_historical_match_rankings.sql`
- `int_footystats_team_match_events.sql`
- `int_squad_player_discipline.sql`

### Marts

Folder:

```text
dbt_world_cup/models/marts/
```

Purpose:

- Create analyst-facing tables.
- These are the tables you would expect a dashboard, notebook, or model to consume.

Start with:

- `mart_team_strength.sql`
- `mart_latest_fifa_rankings.sql`
- `mart_team_event_profile.sql`
- `fct_fixture_schedule.sql`

### Features

Folder:

```text
dbt_world_cup/models/features/
```

Purpose:

- Create model-ready outputs.
- This layer will grow when we connect team-strength features to prediction code.

### BI

Folder:

```text
dbt_world_cup/models/bi/
```

Purpose:

- Create dashboard-facing tables.
- Keep visual/reporting tables separate from model-training feature tables.
- Publish clean inputs for Looker Studio CSV uploads or any other BI tool.

Start with:

- `bi_team_profiles.sql`
- `bi_match_feature_context.sql`
- `bi_historical_competition_summary.sql`

## 3. Query The DuckDB Warehouse

The local warehouse file is:

```text
data/processed/world_cup.duckdb
```

Run quick queries through Python:

```powershell
@'
import duckdb

con = duckdb.connect("data/processed/world_cup.duckdb")

print(con.execute("""
    select *
    from main_marts.mart_team_strength
    where team_name in ('Argentina', 'Brazil', 'France', 'England', 'Mexico', 'United States')
    order by last_10_points_per_match desc
""").fetchdf())
'@ | .\.venv\Scripts\python.exe -
```

Useful tables to inspect:

```text
main_staging.stg_group_fixtures
main_staging.stg_international_results
main_staging.stg_fifa_rankings
main_intermediate.int_historical_team_match_results
main_intermediate.int_team_form_rolling
main_intermediate.int_historical_match_rankings
main_intermediate.int_footystats_team_match_events
main_intermediate.int_squad_player_discipline
main_marts.fct_fixture_schedule
main_marts.mart_team_strength
main_marts.mart_squad_strength
main_marts.mart_team_event_profile
main_marts.mart_latest_fifa_rankings
main_features.features_submission_baseline
main_features.features_world_cup_group_matches
main_bi.bi_team_profiles
main_bi.bi_match_feature_context
main_bi.bi_historical_competition_summary
```

## 4. Use dbt Commands For Learning

List models:

```powershell
.\.venv\Scripts\dbt.exe ls --project-dir dbt_world_cup --profiles-dir dbt_profiles --resource-type model
```

Build one model and its parents:

```powershell
.\.venv\Scripts\dbt.exe build --project-dir dbt_world_cup --profiles-dir dbt_profiles --select +mart_team_strength
```

Build one folder:

```powershell
.\.venv\Scripts\dbt.exe build --project-dir dbt_world_cup --profiles-dir dbt_profiles --select marts
```

Show compiled SQL for a model:

```powershell
.\.venv\Scripts\dbt.exe compile --project-dir dbt_world_cup --profiles-dir dbt_profiles --select mart_team_strength
```

Then inspect:

```text
dbt_world_cup/target/compiled/
```

## 5. The Mental Model

Think of the project like this:

```text
raw CSVs
  -> staging models
  -> intermediate models
  -> marts
  -> feature tables
  -> Python predictions
  -> BI exports
```

The most important current dbt learning example is:

```text
stg_international_results
  -> int_historical_team_match_results
  -> int_team_form_rolling
  -> mart_team_strength
```

That chain shows the core analytics engineering pattern: clean source data, reshape it around the business entity, calculate reusable features, and publish a tested table.

For the new event model, inspect:

```text
stg_footystats_match_stats
  -> int_footystats_team_match_events
  -> mart_team_event_profile
```

Then compare it to:

```text
stg_world_cup_squads + stg_club_player_stats
  -> int_squad_player_discipline
  -> mart_team_event_profile
```

For the point-in-time FIFA ranking join:

```text
stg_fifa_rankings
  -> int_historical_match_rankings
  -> features_historical_match_training
```
