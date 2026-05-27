# dbt Learning Notes

This project uses dbt to model the competition data before Python handles the tournament simulation and submission generation.

## Why dbt Here?

dbt is the transformation layer. In plain terms, it lets us write SQL models, test them, document them, and build them in dependency order.

For this project, dbt helps demonstrate analytics engineering skills:

- Clean raw files into consistent staging views.
- Combine fixtures into analysis-ready intermediate models.
- Build mart tables that a dashboard, notebook, or model can consume.
- Add tests so broken assumptions fail loudly.
- Generate lineage, docs, and repeatable builds.

## Current Layering

### Staging

Files:

- `dbt_world_cup/models/staging/stg_group_fixtures.sql`
- `dbt_world_cup/models/staging/stg_knockout_slots.sql`
- `dbt_world_cup/models/staging/stg_international_results.sql`
- `dbt_world_cup/models/staging/stg_shootouts.sql`

Staging models are thin cleanup layers. They read raw CSVs, rename awkward columns, cast dates, and standardize text.

Example: the raw group file has a `group` column. DuckDB normalizes that to `_group`, so the staging model renames it to `group_letter`. This is a classic staging task: hide raw-source weirdness from the rest of the project.

The historical results staging model also shows a common real-world cleanup: the source includes future fixtures with `NA` scores. For prediction training, we only want completed matches, so `stg_international_results` reads `NA` as null and filters out rows without final scores.

### Intermediate

File:

- `dbt_world_cup/models/intermediate/int_fixture_slots.sql`
- `dbt_world_cup/models/intermediate/int_historical_team_match_results.sql`
- `dbt_world_cup/models/intermediate/int_team_form_rolling.sql`

Intermediate models express business logic that is reusable but not necessarily final reporting output. This model unions group fixtures and knockout slots into one 104-match schedule.

`int_historical_team_match_results` is the first important analytics-engineering reshaping step. The raw results file has one row per match. Most team-strength features need one row per team per match, so this model creates two rows for every match: one from the home team's point of view and one from the away team's point of view.

`int_team_form_rolling` adds prior-match rolling metrics. Notice the word prior: these windows use previous matches only, which avoids leaking the current match result into its own features.

### Marts

Files:

- `dbt_world_cup/models/marts/dim_teams.sql`
- `dbt_world_cup/models/marts/fct_fixture_schedule.sql`
- `dbt_world_cup/models/marts/mart_team_strength.sql`

Mart models are analyst-facing tables. `dim_teams` is a dimension table with one row per team. `fct_fixture_schedule` is a fact-style table with one row per match slot.

`mart_team_strength` summarizes each team's recent international form as of the tournament start date. This is the first table that can feed a real prediction model.

### Features

File:

- `dbt_world_cup/models/features/features_submission_baseline.sql`
- `dbt_world_cup/models/features/features_historical_match_training.sql`
- `dbt_world_cup/models/features/features_world_cup_group_matches.sql`

Feature models are model-ready outputs. The current feature model is intentionally simple, but it establishes the pattern: downstream Python should consume tested dbt tables instead of raw CSVs once the baseline matures.

`features_historical_match_training` is the first supervised-learning table. It has one row per completed historical match, feature columns from each team's prior form, and target columns like `home_score`, `away_score`, and `match_outcome`.

`features_world_cup_group_matches` is the scoring table for the 2026 group stage. It joins group fixtures to the latest team-strength snapshot. Some rows are intentionally incomplete because the competition still has placeholders such as playoff teams; those will need fallback handling in Python.

## Tests

The `schema.yml` files define generic tests like:

- `not_null`
- `unique`
- `accepted_values`

The `tests/` folder holds custom SQL tests:

- `assert_group_stage_has_72_matches.sql`
- `assert_knockout_has_32_slots.sql`
- `assert_international_results_no_negative_scores.sql`
- `assert_team_match_results_two_rows_per_match.sql`
- `assert_shootouts_link_to_results.sql`

In dbt, a test passes when the query returns zero rows. For example, the 72-match test returns a row only if the count is not 72.

## Commands

Run the full dbt build:

```powershell
.\.venv\Scripts\dbt.exe build --project-dir dbt_world_cup --profiles-dir dbt_profiles
```

This runs models and tests together.

Parse the project without building data:

```powershell
.\.venv\Scripts\dbt.exe parse --project-dir dbt_world_cup --profiles-dir dbt_profiles
```

This catches syntax and project configuration issues quickly.

## Why Python Still Exists

dbt is set-based SQL. It is great for cleaning, testing, joining, and aggregating tables.

The knockout bracket is stateful: match 104 depends on winners from matches 101 and 102, which depend on earlier winners. That recursive simulation is easier to read and maintain in Python. So the current boundary is:

- dbt: clean and validate analytical tables.
- Python: simulate group standings, resolve knockout teams, and write workbook-facing predictions.
