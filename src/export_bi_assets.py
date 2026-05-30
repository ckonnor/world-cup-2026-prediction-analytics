from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd

from world_cup.paths import (
    BI_EXPORT_DIR,
    DUCKDB_PATH,
    MODEL_METRICS_V2_PATH,
    MODEL_TEAM_FEATURES_V2_PATH,
    MODEL_TOURNAMENT_SIMULATION_V2_PATH,
    SUBMISSION_GROUP_PREDICTIONS_PATH,
    SUBMISSION_KNOCKOUT_PREDICTIONS_PATH,
    SUBMISSION_VALIDATION_PATH,
)
from world_cup.tournament_rules import build_group_standings


BI_TABLES = {
    "dashboard_team_profiles.csv": "main_bi.bi_team_profiles",
    "dashboard_player_power_profiles.csv": "main_bi.bi_player_power_profiles",
    "dashboard_match_feature_context.csv": "main_bi.bi_match_feature_context",
    "dashboard_historical_competition_summary.csv": (
        "main_bi.bi_historical_competition_summary"
    ),
}


def _require_files(paths: list[Path]) -> None:
    missing_paths = [path for path in paths if not path.exists()]
    if missing_paths:
        missing_text = "\n".join(f"- {path}" for path in missing_paths)
        raise FileNotFoundError(
            "Missing BI export inputs. Run dbt, train_model.py, and "
            f"export_datacamp_submission.py first:\n{missing_text}"
        )


def _scoreline(home_goals: object, away_goals: object) -> str:
    return f"{int(home_goals)}-{int(away_goals)}"


def _winner_team(home_team: object, away_team: object, winner_label: object) -> str:
    if winner_label == "home":
        return str(home_team)
    if winner_label == "away":
        return str(away_team)
    return "Draw"


def _build_dashboard_match_predictions(
    group_predictions: pd.DataFrame,
    knockout_predictions: pd.DataFrame,
) -> pd.DataFrame:
    group_dashboard = group_predictions.assign(
        competition_phase="group",
        round="Group stage",
        multiplier=1.0,
        slot_home=pd.NA,
        slot_away=pd.NA,
        predicted_home_team=group_predictions["home_team"],
        predicted_away_team=group_predictions["away_team"],
        winner_label=group_predictions["winning_team"],
        penalties=False,
    )

    knockout_dashboard = knockout_predictions.assign(
        competition_phase="knockout",
        group=pd.NA,
        home_team=knockout_predictions["predicted_home_team"],
        away_team=knockout_predictions["predicted_away_team"],
        winner_label=knockout_predictions["match_winner"],
    )

    columns = [
        "match_id",
        "competition_phase",
        "group",
        "round",
        "multiplier",
        "date_utc",
        "venue",
        "slot_home",
        "slot_away",
        "home_team",
        "away_team",
        "predicted_home_team",
        "predicted_away_team",
        "predicted_home_goals",
        "predicted_away_goals",
        "corners",
        "yellow_cards",
        "red_cards",
        "winner_label",
        "penalties",
    ]
    dashboard = pd.concat(
        [group_dashboard[columns], knockout_dashboard[columns]],
        ignore_index=True,
    )
    dashboard["match_id"] = dashboard["match_id"].astype(int)
    dashboard["scoreline"] = dashboard.apply(
        lambda row: _scoreline(row["predicted_home_goals"], row["predicted_away_goals"]),
        axis=1,
    )
    dashboard["total_goals"] = (
        dashboard["predicted_home_goals"].astype(int)
        + dashboard["predicted_away_goals"].astype(int)
    )
    dashboard["total_cards"] = (
        dashboard["yellow_cards"].astype(int) + dashboard["red_cards"].astype(int)
    )
    dashboard["predicted_winner_team"] = dashboard.apply(
        lambda row: _winner_team(
            row["predicted_home_team"],
            row["predicted_away_team"],
            row["winner_label"],
        ),
        axis=1,
    )
    dashboard["is_draw_scoreline"] = (
        dashboard["predicted_home_goals"].astype(int)
        == dashboard["predicted_away_goals"].astype(int)
    )
    dashboard["penalties"] = dashboard["penalties"].astype(bool)
    return dashboard.sort_values("match_id").reset_index(drop=True)


def _build_dashboard_group_standings(group_predictions: pd.DataFrame) -> pd.DataFrame:
    standings = build_group_standings(group_predictions)
    return standings.rename(
        columns={
            "group": "group_letter",
            "team": "team_name",
            "played": "matches_played",
        }
    )[
        [
            "group_letter",
            "group_rank",
            "team_name",
            "matches_played",
            "wins",
            "draws",
            "losses",
            "points",
            "goals_for",
            "goals_against",
            "goal_difference",
        ]
    ]


def _flatten_metric_targets(metrics: dict[str, object]) -> pd.DataFrame:
    metric_targets = metrics.get("metric_targets", {})
    rows = []
    for metric_name, metric_config in metric_targets.items():
        if not isinstance(metric_config, dict):
            continue
        rows.append(
            {
                "metric_name": metric_name,
                "current_value": metric_config["current"],
                "direction": metric_config["direction"],
                "guardrail": metric_config["guardrail"],
                "target": metric_config["target"],
                "stretch": metric_config["stretch"],
                "status": metric_config["status"],
            }
        )
    reconciled_holdout = metrics.get("reconciled_holdout", {})
    if isinstance(reconciled_holdout, dict):
        blended_outcome_accuracy = float(reconciled_holdout["match_outcome_accuracy"])
        rows.append(
            {
                "metric_name": "blended_scoreline_outcome_accuracy",
                "current_value": blended_outcome_accuracy,
                "direction": "higher",
                "guardrail": 0.58,
                "target": 0.62,
                "stretch": 0.65,
                "status": _metric_status(blended_outcome_accuracy, 0.58, 0.62, 0.65),
            }
        )
    return pd.DataFrame(rows)


def _metric_status(value: float, guardrail: float, target: float, stretch: float) -> str:
    if value >= stretch:
        return "stretch"
    if value >= target:
        return "target"
    if value >= guardrail:
        return "guardrail"
    return "below_guardrail"


def _build_dashboard_data_quality(validation: dict[str, object]) -> pd.DataFrame:
    rows = []
    row_counts = validation.get("row_counts", {})
    if isinstance(row_counts, dict):
        rows.extend(
            {
                "check_group": "row_count",
                "check_name": str(name),
                "check_value": int(value),
            }
            for name, value in row_counts.items()
        )

    group_distribution = validation.get("group_result_distribution", {})
    if isinstance(group_distribution, dict):
        rows.extend(
            {
                "check_group": "group_result_distribution",
                "check_name": str(name),
                "check_value": int(value),
            }
            for name, value in group_distribution.items()
        )

    knockout_penalties = validation.get("knockout_penalties", {})
    if isinstance(knockout_penalties, dict):
        rows.extend(
            {
                "check_group": "knockout_penalties",
                "check_name": str(name),
                "check_value": int(value),
            }
            for name, value in knockout_penalties.items()
        )

    rows.append(
        {
            "check_group": "submission_validation",
            "check_name": "valid",
            "check_value": int(bool(validation.get("valid"))),
        }
    )
    return pd.DataFrame(rows)


def _load_dbt_table(table_name: str) -> pd.DataFrame:
    if not DUCKDB_PATH.exists():
        raise FileNotFoundError(f"{DUCKDB_PATH} does not exist. Run dbt build first.")
    with duckdb.connect(str(DUCKDB_PATH), read_only=True) as con:
        return con.execute(f"select * from {table_name}").fetchdf()


def _sort_export_frame(output_name: str, frame: pd.DataFrame) -> pd.DataFrame:
    sort_keys = {
        "dashboard_group_standings.csv": ["group_letter", "group_rank", "team_name"],
        "dashboard_data_quality.csv": ["check_group", "check_name"],
        "dashboard_team_profiles.csv": ["team_name"],
        "dashboard_player_power_profiles.csv": [
            "team_name",
            "team_player_power_rank",
            "player_name",
        ],
        "dashboard_match_feature_context.csv": ["match_id"],
        "dashboard_historical_competition_summary.csv": ["match_year", "tournament"],
    }
    columns = [column for column in sort_keys.get(output_name, []) if column in frame.columns]
    if not columns:
        return frame
    return frame.sort_values(columns).reset_index(drop=True)


def export_bi_assets() -> list[Path]:
    _require_files(
        [
            DUCKDB_PATH,
            MODEL_METRICS_V2_PATH,
            MODEL_TEAM_FEATURES_V2_PATH,
            MODEL_TOURNAMENT_SIMULATION_V2_PATH,
            SUBMISSION_GROUP_PREDICTIONS_PATH,
            SUBMISSION_KNOCKOUT_PREDICTIONS_PATH,
            SUBMISSION_VALIDATION_PATH,
        ]
    )

    BI_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    group_predictions = pd.read_csv(SUBMISSION_GROUP_PREDICTIONS_PATH)
    knockout_predictions = pd.read_csv(SUBMISSION_KNOCKOUT_PREDICTIONS_PATH)
    metrics = json.loads(MODEL_METRICS_V2_PATH.read_text(encoding="utf-8"))
    model_team_features = pd.read_csv(MODEL_TEAM_FEATURES_V2_PATH)
    tournament_simulation = pd.read_csv(MODEL_TOURNAMENT_SIMULATION_V2_PATH)
    validation = json.loads(SUBMISSION_VALIDATION_PATH.read_text(encoding="utf-8"))

    exports = {
        "dashboard_match_predictions.csv": _build_dashboard_match_predictions(
            group_predictions,
            knockout_predictions,
        ),
        "dashboard_group_standings.csv": _build_dashboard_group_standings(
            group_predictions,
        ),
        "dashboard_model_metrics.csv": _flatten_metric_targets(metrics),
        "dashboard_data_quality.csv": _build_dashboard_data_quality(validation),
        "dashboard_tournament_simulation.csv": tournament_simulation,
    }
    for output_name, table_name in BI_TABLES.items():
        exports[output_name] = _load_dbt_table(table_name)
    exports["dashboard_team_profiles.csv"] = exports["dashboard_team_profiles.csv"].merge(
        model_team_features,
        on="team_model_name",
        how="left",
    )

    written_paths = []
    for output_name, frame in exports.items():
        output_path = BI_EXPORT_DIR / output_name
        _sort_export_frame(output_name, frame).to_csv(output_path, index=False)
        written_paths.append(output_path)
    return written_paths


def main() -> None:
    written_paths = export_bi_assets()
    print("Wrote BI dashboard extracts:")
    for path in written_paths:
        print(f"- {path}")


if __name__ == "__main__":
    main()
