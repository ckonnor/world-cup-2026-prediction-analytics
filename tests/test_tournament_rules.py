from __future__ import annotations

import pandas as pd

from world_cup.tournament_rules import build_group_standings, resolve_knockout_slot


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


def test_resolve_knockout_slot_handles_group_and_prior_match_slots() -> None:
    standings = pd.DataFrame(
        [
            {
                "group": "A",
                "team": "Winner A",
                "group_rank": 1,
                "points": 9,
                "goal_difference": 4,
                "goals_for": 7,
            },
            {
                "group": "A",
                "team": "Runner A",
                "group_rank": 2,
                "points": 6,
                "goal_difference": 2,
                "goals_for": 5,
            },
            {
                "group": "A",
                "team": "Third A",
                "group_rank": 3,
                "points": 4,
                "goal_difference": 0,
                "goals_for": 4,
            },
            {
                "group": "B",
                "team": "Third B",
                "group_rank": 3,
                "points": 5,
                "goal_difference": 1,
                "goals_for": 4,
            },
        ]
    )
    used_third_groups: set[str] = set()
    match_results = {73: {"winner_team": "Winner 73", "loser_team": "Loser 73"}}

    assert (
        resolve_knockout_slot("Winner Group A", standings, match_results, used_third_groups)
        == "Winner A"
    )
    assert (
        resolve_knockout_slot("Runner-up Group A", standings, match_results, used_third_groups)
        == "Runner A"
    )
    assert (
        resolve_knockout_slot("Winner Match 73", standings, match_results, used_third_groups)
        == "Winner 73"
    )
    assert (
        resolve_knockout_slot("Loser Match 73", standings, match_results, used_third_groups)
        == "Loser 73"
    )
    assert (
        resolve_knockout_slot("Best 3rd (Groups A/B)", standings, match_results, used_third_groups)
        == "Third B"
    )
    assert used_third_groups == {"B"}
