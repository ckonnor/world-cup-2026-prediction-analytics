from __future__ import annotations

import pandas as pd

from export_bi_assets import (
    _build_dashboard_group_standings,
    _build_dashboard_match_predictions,
    _flatten_metric_targets,
)


def test_build_dashboard_match_predictions_normalizes_group_and_knockout_rows() -> None:
    group_predictions = pd.DataFrame(
        [
            {
                "match_id": 1,
                "group": "A",
                "home_team": "Mexico",
                "away_team": "South Africa",
                "date_utc": "2026-06-11T19:00:00Z",
                "venue": "Estadio Azteca",
                "predicted_home_goals": 2,
                "predicted_away_goals": 0,
                "corners": 9,
                "yellow_cards": 3,
                "red_cards": 0,
                "winning_team": "home",
            }
        ]
    )
    knockout_predictions = pd.DataFrame(
        [
            {
                "match_id": 73,
                "round": "Round of 32",
                "multiplier": 1.0,
                "date_utc": "2026-06-28T19:00:00Z",
                "venue": "SoFi Stadium",
                "slot_home": "Runner-up Group A",
                "slot_away": "Runner-up Group B",
                "predicted_home_team": "South Korea",
                "predicted_away_team": "Canada",
                "predicted_home_goals": 1,
                "predicted_away_goals": 1,
                "corners": 9,
                "yellow_cards": 4,
                "red_cards": 0,
                "match_winner": "away",
                "penalties": True,
            }
        ]
    )

    dashboard = _build_dashboard_match_predictions(group_predictions, knockout_predictions)

    assert dashboard["scoreline"].tolist() == ["2-0", "1-1"]
    assert dashboard["predicted_winner_team"].tolist() == ["Mexico", "Canada"]
    assert dashboard["total_goals"].tolist() == [2, 2]
    assert dashboard["penalties"].tolist() == [False, True]


def test_build_dashboard_group_standings_returns_ranked_groups() -> None:
    group_predictions = pd.DataFrame(
        [
            {
                "group": "A",
                "home_team": "Team A",
                "away_team": "Team B",
                "predicted_home_goals": 2,
                "predicted_away_goals": 0,
            },
            {
                "group": "A",
                "home_team": "Team C",
                "away_team": "Team D",
                "predicted_home_goals": 1,
                "predicted_away_goals": 1,
            },
        ]
    )

    standings = _build_dashboard_group_standings(group_predictions)

    assert standings.loc[0, "team_name"] == "Team A"
    assert standings.loc[0, "points"] == 3
    assert {"group_letter", "group_rank", "goal_difference"}.issubset(standings.columns)


def test_flatten_metric_targets_builds_dashboard_table() -> None:
    metrics = {
        "metric_targets": {
            "direct_outcome_accuracy": {
                "current": 0.617,
                "direction": "higher",
                "guardrail": 0.58,
                "target": 0.62,
                "stretch": 0.65,
                "status": "guardrail",
            }
        }
    }

    dashboard = _flatten_metric_targets(metrics)

    assert dashboard.to_dict("records") == [
        {
            "metric_name": "direct_outcome_accuracy",
            "current_value": 0.617,
            "direction": "higher",
            "guardrail": 0.58,
            "target": 0.62,
            "stretch": 0.65,
            "status": "guardrail",
        }
    ]
