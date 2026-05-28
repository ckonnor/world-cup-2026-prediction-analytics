from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from world_cup.baseline import (
    build_group_predictions,
    build_group_standings,
    build_knockout_predictions,
)


def test_group_standings_can_use_strength_tiebreaker() -> None:
    predictions = pd.DataFrame(
        [
            {
                "group": "A",
                "home_team": "Team A",
                "away_team": "Team B",
                "predicted_home_goals": 1,
                "predicted_away_goals": 1,
            }
        ]
    )

    standings = build_group_standings(
        predictions,
        team_tiebreak_strengths={"Team A": 1.0, "Team B": 2.0},
    )

    assert standings.loc[0, "team"] == "Team B"


def test_baseline_outputs_match_datacamp_workbook_shape() -> None:
    if not Path("data/raw/group_fixtures.csv").exists() or not Path("data/raw/knockout_slots.csv").exists():
        pytest.skip("DataCamp raw files are not available in this environment.")

    group_fixtures = pd.read_csv("data/raw/group_fixtures.csv")
    knockout_slots = pd.read_csv("data/raw/knockout_slots.csv")

    group_predictions = build_group_predictions(group_fixtures)
    knockout_predictions = build_knockout_predictions(knockout_slots, group_predictions)

    assert len(group_predictions) == 72
    assert len(knockout_predictions) == 32

    assert {
        "predicted_home_goals",
        "predicted_away_goals",
        "corners",
        "yellow_cards",
        "red_cards",
        "winning_team",
    }.issubset(group_predictions.columns)
    assert set(group_predictions["winning_team"]).issubset({"home", "away", "draw"})

    assert {
        "predicted_home_team",
        "predicted_away_team",
        "predicted_home_goals",
        "predicted_away_goals",
        "corners",
        "yellow_cards",
        "red_cards",
        "match_winner",
        "penalties",
    }.issubset(knockout_predictions.columns)
    assert set(knockout_predictions["match_winner"]).issubset({"home", "away"})
    assert knockout_predictions["penalties"].map(type).eq(bool).all()
