from __future__ import annotations

import re
from collections import defaultdict

import pandas as pd


def build_group_standings(
    group_predictions: pd.DataFrame,
    team_tiebreak_strengths: dict[str, float] | None = None,
) -> pd.DataFrame:
    standings: dict[tuple[str, str], dict[str, object]] = defaultdict(
        lambda: {
            "played": 0,
            "points": 0,
            "goals_for": 0,
            "goals_against": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
        }
    )

    for row in group_predictions.itertuples(index=False):
        group_letter = getattr(row, "group")
        home_team = getattr(row, "home_team")
        away_team = getattr(row, "away_team")
        home_goals = int(getattr(row, "predicted_home_goals"))
        away_goals = int(getattr(row, "predicted_away_goals"))

        home = standings[(group_letter, home_team)]
        away = standings[(group_letter, away_team)]

        home["group"] = away["group"] = group_letter
        home["team"] = home_team
        away["team"] = away_team
        home["played"] += 1
        away["played"] += 1
        home["goals_for"] += home_goals
        home["goals_against"] += away_goals
        away["goals_for"] += away_goals
        away["goals_against"] += home_goals

        if home_goals > away_goals:
            home["points"] += 3
            home["wins"] += 1
            away["losses"] += 1
        elif away_goals > home_goals:
            away["points"] += 3
            away["wins"] += 1
            home["losses"] += 1
        else:
            home["points"] += 1
            away["points"] += 1
            home["draws"] += 1
            away["draws"] += 1

    table = pd.DataFrame(standings.values())
    table["goal_difference"] = table["goals_for"] - table["goals_against"]
    sort_columns = ["group", "points", "goal_difference", "goals_for"]
    ascending = [True, False, False, False]
    if team_tiebreak_strengths is not None:
        table["_tiebreak_strength"] = table["team"].map(team_tiebreak_strengths).fillna(0.0)
        sort_columns.append("_tiebreak_strength")
        ascending.append(False)
    sort_columns.append("team")
    ascending.append(True)
    table = table.sort_values(
        sort_columns,
        ascending=ascending,
    )
    table["group_rank"] = table.groupby("group").cumcount() + 1
    return table.reset_index(drop=True)


def _team_at_group_rank(standings: pd.DataFrame, group_letter: str, rank: int) -> str:
    rows = standings[(standings["group"] == group_letter) & (standings["group_rank"] == rank)]
    if rows.empty:
        raise ValueError(f"Could not resolve Group {group_letter} rank {rank}.")
    return str(rows.iloc[0]["team"])


def _parse_group_slot(slot_label: str, standings: pd.DataFrame, used_third_groups: set[str]) -> str:
    winner_match = re.fullmatch(r"Winner Group ([A-L])", slot_label)
    if winner_match:
        return _team_at_group_rank(standings, winner_match.group(1), 1)

    runner_up_match = re.fullmatch(r"Runner-up Group ([A-L])", slot_label)
    if runner_up_match:
        return _team_at_group_rank(standings, runner_up_match.group(1), 2)

    best_third_match = re.fullmatch(r"Best 3rd \(Groups ([A-L/]+)\)", slot_label)
    if best_third_match:
        eligible_groups = best_third_match.group(1).split("/")
        third_place = standings[standings["group_rank"] == 3].copy()
        sort_columns = ["points", "goal_difference", "goals_for"]
        ascending = [False, False, False]
        if "_tiebreak_strength" in third_place.columns:
            sort_columns.append("_tiebreak_strength")
            ascending.append(False)
        sort_columns.append("team")
        ascending.append(True)
        third_place = third_place.sort_values(sort_columns, ascending=ascending)
        for row in third_place.itertuples(index=False):
            group_letter = getattr(row, "group")
            if group_letter in eligible_groups and group_letter not in used_third_groups:
                used_third_groups.add(group_letter)
                return getattr(row, "team")

        return _team_at_group_rank(standings, eligible_groups[0], 3)

    return slot_label


def resolve_knockout_slot(
    slot_label: str,
    standings: pd.DataFrame,
    match_results: dict[int, dict[str, str]],
    used_third_groups: set[str],
) -> str:
    prior_match = re.fullmatch(r"(Winner|Loser) Match ([0-9]+)", slot_label)
    if prior_match:
        result_type = prior_match.group(1).lower()
        match_id = int(prior_match.group(2))
        return match_results[match_id][f"{result_type}_team"]

    return _parse_group_slot(slot_label, standings, used_third_groups)
