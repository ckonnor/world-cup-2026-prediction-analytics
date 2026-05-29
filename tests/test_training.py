from __future__ import annotations

import numpy as np
import pandas as pd

from train_model import (
    _best_draw_probability_threshold,
    _is_tournament_focused_match,
    _metric_target_status,
    _predict_event_counts,
    _select_blended_scoreline,
    _scoreline_probability_grid,
    outcome_from_scores,
)


def test_outcome_from_scores() -> None:
    assert outcome_from_scores(2, 1) == "home"
    assert outcome_from_scores(1, 2) == "away"
    assert outcome_from_scores(1, 1) == "draw"


def test_predict_event_counts_uses_team_profile() -> None:
    matches = pd.DataFrame([{"home_team": "A", "away_team": "B"}])
    team_event_profile = pd.DataFrame(
        [
            {
                "team_name": "A",
                "avg_corners_for": 5.0,
                "avg_corners_against": 4.0,
                "blended_yellow_cards_for": 2.0,
                "avg_yellow_cards_against": 1.5,
                "blended_red_cards_for": 0.1,
                "avg_red_cards_against": 0.1,
            },
            {
                "team_name": "B",
                "avg_corners_for": 6.0,
                "avg_corners_against": 5.0,
                "blended_yellow_cards_for": 2.2,
                "avg_yellow_cards_against": 2.0,
                "blended_red_cards_for": 0.2,
                "avg_red_cards_against": 0.1,
            },
        ]
    )

    result = _predict_event_counts(matches, team_event_profile)

    assert result.loc[0, "corners"] == 10
    assert result.loc[0, "yellow_cards"] == 4
    assert result.loc[0, "red_cards"] == 0


def test_select_blended_scoreline_balances_goals_and_outcome_probabilities() -> None:
    classes = np.array(["away", "draw", "home"])

    assert _select_blended_scoreline(
        1.2,
        1.4,
        np.array([0.04, 0.30, 0.66]),
        classes,
        0.25,
    ) == (1, 1)
    assert _select_blended_scoreline(
        1.2,
        1.4,
        np.array([0.04, 0.30, 0.66]),
        classes,
        0.60,
    ) == (1, 0)


def test_scoreline_probability_grid_is_normalized() -> None:
    classes = np.array(["away", "draw", "home"])
    grid = _scoreline_probability_grid(
        1.3,
        0.9,
        np.array([0.20, 0.25, 0.55]),
        classes,
        0.30,
    )

    assert len(grid) == 81
    assert np.isclose(grid["probability"].sum(), 1.0)
    assert {"home", "draw", "away"} == set(grid["outcome"])


def test_metric_target_status_handles_higher_and_lower_metrics() -> None:
    assert _metric_target_status(0.62, "higher", 0.55, 0.60, 0.65) == "target"
    assert _metric_target_status(0.84, "lower", 0.95, 0.90, 0.86) == "stretch"


def test_best_draw_probability_threshold_keeps_draw_guardrail() -> None:
    actual = pd.Series(["home", "draw", "away", "home", "draw"])
    classes = pd.Series(["away", "draw", "home"]).to_numpy()
    probabilities = pd.DataFrame(
        [
            [0.20, 0.20, 0.60],
            [0.10, 0.35, 0.55],
            [0.55, 0.20, 0.25],
            [0.15, 0.25, 0.60],
            [0.10, 0.36, 0.54],
        ]
    ).to_numpy()

    assert _best_draw_probability_threshold(actual, probabilities, classes) <= 0.36


def test_tournament_focused_match_excludes_friendlies() -> None:
    data = pd.DataFrame(
        {
            "tournament": [
                "FIFA World Cup",
                "FIFA World Cup qualification",
                "Friendly",
            ]
        }
    )

    assert _is_tournament_focused_match(data).tolist() == [True, True, False]
