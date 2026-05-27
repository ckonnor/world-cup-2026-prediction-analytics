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

Staging models are thin cleanup layers. They read raw CSVs, rename awkward columns, cast dates, and standardize text.

Example: the raw group file has a `group` column. DuckDB normalizes that to `_group`, so the staging model renames it to `group_letter`. This is a classic staging task: hide raw-source weirdness from the rest of the project.

### Intermediate

File:

- `dbt_world_cup/models/intermediate/int_fixture_slots.sql`

Intermediate models express business logic that is reusable but not necessarily final reporting output. This model unions group fixtures and knockout slots into one 104-match schedule.

### Marts

Files:

- `dbt_world_cup/models/marts/dim_teams.sql`
- `dbt_world_cup/models/marts/fct_fixture_schedule.sql`

Mart models are analyst-facing tables. `dim_teams` is a dimension table with one row per team. `fct_fixture_schedule` is a fact-style table with one row per match slot.

### Features

File:

- `dbt_world_cup/models/features/features_submission_baseline.sql`

Feature models are model-ready outputs. The current feature model is intentionally simple, but it establishes the pattern: downstream Python should consume tested dbt tables instead of raw CSVs once the baseline matures.

## Tests

The `schema.yml` files define generic tests like:

- `not_null`
- `unique`
- `accepted_values`

The `tests/` folder holds custom SQL tests:

- `assert_group_stage_has_72_matches.sql`
- `assert_knockout_has_32_slots.sql`

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
