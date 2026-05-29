# dbt Docs and Lineage

dbt docs are the best way to show the transformation graph behind the dashboard. The project already includes schema files and tests across staging, intermediate, marts, features, and BI models, so generated docs can explain both lineage and model contracts.

## Generate dbt Docs Locally

dbt docs require the same local raw files and DuckDB profile used by the full pipeline.

```powershell
.\.venv\Scripts\dbt.exe docs generate --project-dir dbt_world_cup --profiles-dir dbt_profiles
.\.venv\Scripts\dbt.exe docs serve --project-dir dbt_world_cup --profiles-dir dbt_profiles
```

The generated site lives under `dbt_world_cup/target/`, which is intentionally ignored by git.

## Lineage To Highlight

The strongest lineage story is:

```mermaid
flowchart LR
    stg_results["stg_international_results"]
    stg_rankings["stg_fifa_rankings"]
    stg_squads["stg_world_cup_squads"]
    stg_events["stg_footystats_match_stats"]
    stg_fixtures["stg_group_fixtures"]

    int_form["int_team_form_rolling"]
    int_rankings["int_historical_match_rankings"]
    mart_strength["mart_team_strength"]
    mart_rankings["mart_latest_fifa_rankings"]
    mart_squad["mart_squad_strength"]
    mart_events["mart_team_event_profile"]
    features_train["features_historical_match_training"]
    features_group["features_world_cup_group_matches"]
    bi_profiles["bi_team_profiles"]
    bi_context["bi_match_feature_context"]

    stg_results --> int_form --> mart_strength
    stg_results --> int_rankings --> features_train
    stg_rankings --> int_rankings
    stg_rankings --> mart_rankings
    stg_squads --> mart_squad
    stg_events --> mart_events
    stg_fixtures --> features_group
    mart_strength --> features_group
    mart_rankings --> features_group
    mart_squad --> features_group
    mart_events --> features_group
    mart_strength --> bi_profiles
    mart_rankings --> bi_profiles
    mart_squad --> bi_profiles
    mart_events --> bi_profiles
    features_group --> bi_context
```

## What To Screenshot For A Portfolio

Good screenshots for a project page or interview deck:

- the dbt DAG centered on `features_world_cup_group_matches`
- the dbt DAG centered on `bi_team_profiles`
- the model detail page for `features_historical_match_training`, showing point-in-time fields and tests
- the test results page showing row-count, uniqueness, and leakage checks

These screenshots are better than generic code screenshots because they show how the project is governed.
