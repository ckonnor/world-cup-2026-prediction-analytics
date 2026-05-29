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
- `dbt_world_cup/models/staging/stg_world_cup_squads.sql`
- `dbt_world_cup/models/staging/stg_footystats_match_stats.sql`
- `dbt_world_cup/models/staging/stg_club_player_stats.sql`
- `dbt_world_cup/models/staging/stg_fifa_rankings.sql`
- `dbt_world_cup/models/staging/stg_international_match_features.sql`
- `dbt_world_cup/models/staging/stg_international_player_aggregates.sql`

Staging models are thin cleanup layers. They read raw CSVs, rename awkward columns, cast dates, and standardize text.

Example: the raw group file has a `group` column. DuckDB normalizes that to `_group`, so the staging model renames it to `group_letter`. This is a classic staging task: hide raw-source weirdness from the rest of the project.

The group fixture staging model also resolves the DataCamp playoff placeholders through the `team_name_resolution` seed. That means the raw CSV still says values like `UEFA Playoff A`, but dbt exposes the current team name, the raw team name, and a historical-source `model_team_name` used for joins. This is the audit trail we want in analytics engineering: do not overwrite raw data; document and test the transformation.

The historical results staging model also shows a common real-world cleanup: the source includes future fixtures with `NA` scores. For prediction training, we only want completed matches, so `stg_international_results` reads `NA` as null and filters out rows without final scores.

`stg_world_cup_squads` stages the downloaded squad player rows. It casts ages, caps, goals, shirt numbers, and timestamps into usable types and keeps one row per player. This is another common staging pattern: keep the source grain intact first, then aggregate later.

`stg_footystats_match_stats` and `stg_club_player_stats` stage the new event sources. The match stats keep one row per match with team corners/cards. The club player stats keep one row per player-season with minutes, yellow cards, red cards, fouls, and a normalized player key used for matching.

`stg_fifa_rankings` keeps one row per team per ranking date. It is a good staging example because it combines historical and current ranking sources into one consistent schema before any modeling joins happen.

`stg_international_match_features` keeps external Kaggle match features separate from our core results source. This lets us test extra Elo, form, and player aggregate signals without losing track of where those fields came from.

`stg_international_player_aggregates` keeps country-level player ratings by EA Sports/FIFA version. The mart layer later picks the newest row per team for 2026 scoring.

The project now also has two small dbt macros in `dbt_world_cup/macros/normalization.sql`: one for canonical team names and one for normalized player-name keys. A macro is reusable SQL text. We use it so every model normalizes names the same way.

### Intermediate

File:

- `dbt_world_cup/models/intermediate/int_fixture_slots.sql`
- `dbt_world_cup/models/intermediate/int_historical_team_match_results.sql`
- `dbt_world_cup/models/intermediate/int_team_form_rolling.sql`
- `dbt_world_cup/models/intermediate/int_footystats_team_match_events.sql`
- `dbt_world_cup/models/intermediate/int_squad_player_discipline.sql`
- `dbt_world_cup/models/intermediate/int_historical_match_rankings.sql`

Intermediate models express business logic that is reusable but not necessarily final reporting output. This model unions group fixtures and knockout slots into one 104-match schedule.

`int_historical_team_match_results` is the first important analytics-engineering reshaping step. The raw results file has one row per match. Most team-strength features need one row per team per match, so this model creates two rows for every match: one from the home team's point of view and one from the away team's point of view.

`int_team_form_rolling` adds prior-match rolling metrics. Notice the word prior: these windows use previous matches only, which avoids leaking the current match result into its own features.

`int_footystats_team_match_events` reshapes each event match into two rows, one from each team's point of view. This mirrors `int_historical_team_match_results` and gives us `corners_for`, `corners_against`, `yellow_cards_for`, and related fields.

`int_squad_player_discipline` joins squad players to club player stats by normalized player name and country code. This is intentionally an intermediate model because it is reusable evidence, not yet the final team-level answer.

`int_historical_match_rankings` is a point-in-time join. For each historical match, it finds the latest FIFA ranking published before the match date for both teams. This is important because using future rankings would leak information from after the match.

### Marts

Files:

- `dbt_world_cup/models/marts/dim_teams.sql`
- `dbt_world_cup/models/marts/fct_fixture_schedule.sql`
- `dbt_world_cup/models/marts/mart_team_strength.sql`
- `dbt_world_cup/models/marts/mart_squad_strength.sql`
- `dbt_world_cup/models/marts/mart_team_event_profile.sql`
- `dbt_world_cup/models/marts/mart_latest_fifa_rankings.sql`
- `dbt_world_cup/models/marts/mart_external_player_strength.sql`

Mart models are analyst-facing tables. `dim_teams` is a dimension table with one row per team. `fct_fixture_schedule` is a fact-style table with one row per match slot.

`mart_team_strength` summarizes each team's recent international form as of the tournament start date. This is the first table that can feed a real prediction model.

`mart_squad_strength` summarizes current squad rows into team-level features: squad size, position counts, total caps, total goals, attacking goals, defensive caps, top-five caps, top-five goals, and standardized international-pedigree scores. This is where dbt changes player-grain data into model-grain data.

`mart_team_event_profile` summarizes corners and cards into one row per World Cup team. It uses weighted international match-event rates for corners and blends international cards with matched club player discipline for yellow/red card risk.

`mart_latest_fifa_rankings` publishes the newest ranking snapshot per team. Python uses it when scoring 2026 fixtures and knockout matchups that are resolved dynamically.

`mart_external_player_strength` publishes the newest external player aggregate row per team. It also derives dashboard-ready star-power fields from max overall, average overall, attack, shooting, passing, and pace. Python uses those current player-strength proxies for the direct outcome model.

### Features

File:

- `dbt_world_cup/models/features/features_submission_baseline.sql`
- `dbt_world_cup/models/features/features_historical_match_training.sql`
- `dbt_world_cup/models/features/features_world_cup_group_matches.sql`

Feature models are model-ready outputs. The current feature model is intentionally simple, but it establishes the pattern: downstream Python should consume tested dbt tables instead of raw CSVs once the baseline matures.

`features_historical_match_training` is the first supervised-learning table. It has one row per completed historical match, feature columns from each team's prior form, and target columns like `home_score`, `away_score`, and `match_outcome`.

`features_world_cup_group_matches` is the scoring table for the 2026 group stage. It joins group fixtures to the latest team-strength snapshot using the model team names from staging. Because the playoff placeholders are resolved before this join, every group-stage fixture now has team-strength features.

The same feature table also joins squad strength when a team has a published roster. `has_complete_squad_features` is useful when inspecting model inputs because some teams may not have squad data yet.

The historical training table now also carries star-power differentials from `stg_international_match_features`. Those fields are intentionally produced in dbt so the model can consume named, inspectable columns instead of rebuilding the same player-quality logic inside Python.

It now joins `mart_team_event_profile` too. The fields `expected_total_corners`, `expected_total_yellow_cards`, and `expected_total_red_cards` are the dbt-side event expectations that Python rounds into workbook predictions.

### BI

Files:

- `dbt_world_cup/models/bi/bi_team_profiles.sql`
- `dbt_world_cup/models/bi/bi_match_feature_context.sql`
- `dbt_world_cup/models/bi/bi_historical_competition_summary.sql`

The BI layer is dashboard-facing. These models intentionally select and rename fields for visualization instead of training. This is a useful analytics engineering distinction: feature tables optimize for model code, while BI tables optimize for clear consumption by analysts, hiring managers, and dashboard users.

`bi_team_profiles` is the main team comparison table. `bi_match_feature_context` explains group-stage predictions through feature differences. `bi_historical_competition_summary` gives historical context for the training data.

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
- `assert_group_fixtures_no_unresolved_playoff_placeholders.sql`
- `assert_footystats_team_events_two_rows_per_match.sql`
- `assert_team_event_profile_has_world_cup_teams.sql`
- `assert_bi_team_profiles_has_48_teams.sql`
- `assert_bi_match_feature_context_has_72_matches.sql`

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

For the new cards/corners work, read this dbt chain:

```text
stg_footystats_match_stats
  -> int_footystats_team_match_events
  -> mart_team_event_profile
  -> features_world_cup_group_matches
```

And for player-level discipline:

```text
stg_world_cup_squads + stg_club_player_stats + team_country_codes
  -> int_squad_player_discipline
  -> mart_team_event_profile
```

For FIFA rankings:

```text
stg_fifa_rankings
  -> int_historical_match_rankings
  -> features_historical_match_training
```

And for 2026 scoring:

```text
stg_fifa_rankings
  -> mart_latest_fifa_rankings
  -> Python scoring features
```

For dashboarding:

```text
marts + features
  -> bi models
  -> src/export_bi_assets.py
  -> data/bi_exports/*.csv
```
