from __future__ import annotations

import re
import hashlib
from collections import defaultdict

import pandas as pd


GROUP_PREDICTION_COLUMNS = [
    "predicted_home_goals",
    "predicted_away_goals",
    "corners",
    "yellow_cards",
    "red_cards",
    "winning_team",
]

KNOCKOUT_PREDICTION_COLUMNS = [
    "predicted_home_team",
    "predicted_away_team",
    "predicted_home_goals",
    "predicted_away_goals",
    "corners",
    "yellow_cards",
    "red_cards",
    "match_winner",
    "penalties",
]


def _stable_int(*parts: object) -> int:
    key = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def _score_prediction(match_id: object, home_team: str, away_team: str) -> tuple[int, int]:
    seed = _stable_int(match_id, home_team, away_team)
    return [0, 1, 1, 2, 2, 3][seed % 6], [0, 0, 1, 1, 2, 2][(seed // 7) % 6]


def _group_winner(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home"
    if away_goals > home_goals:
        return "away"
    return "draw"


def _match_totals(seed: int) -> dict[str, int]:
    return {
        "corners": 7 + (seed % 7),
        "yellow_cards": 2 + ((seed // 11) % 5),
        "red_cards": 1 if seed % 89 == 0 else 0,
    }


def _group_prediction_row(row: object) -> dict[str, object]:
    home_team = getattr(row, "home_team")
    away_team = getattr(row, "away_team")
    match_id = getattr(row, "match_id")
    seed = _stable_int(match_id, home_team, away_team)
    home_goals, away_goals = _score_prediction(match_id, home_team, away_team)

    return {
        **row._asdict(),
        "predicted_home_goals": home_goals,
        "predicted_away_goals": away_goals,
        **_match_totals(seed),
        "winning_team": _group_winner(home_goals, away_goals),
    }


def build_group_predictions(group_fixtures: pd.DataFrame) -> pd.DataFrame:
    predictions = [_group_prediction_row(row) for row in group_fixtures.itertuples(index=False)]
    return pd.DataFrame(predictions)[[*group_fixtures.columns, *GROUP_PREDICTION_COLUMNS]]


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


def _parse_group_slot(slot_label: str, standings: pd.DataFrame, used_third_groups: set[str]) -> str:
    winner_match = re.fullmatch(r"Winner Group ([A-L])", slot_label)
    if winner_match:
        group_letter = winner_match.group(1)
        return _team_at_group_rank(standings, group_letter, 1)

    runner_up_match = re.fullmatch(r"Runner-up Group ([A-L])", slot_label)
    if runner_up_match:
        group_letter = runner_up_match.group(1)
        return _team_at_group_rank(standings, group_letter, 2)

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

        fallback_group = eligible_groups[0]
        return _team_at_group_rank(standings, fallback_group, 3)

    return slot_label


def _team_at_group_rank(standings: pd.DataFrame, group_letter: str, rank: int) -> str:
    rows = standings[(standings["group"] == group_letter) & (standings["group_rank"] == rank)]
    if rows.empty:
        raise ValueError(f"Could not resolve Group {group_letter} rank {rank}.")
    return str(rows.iloc[0]["team"])


def _resolve_slot(
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


def resolve_knockout_slot(
    slot_label: str,
    standings: pd.DataFrame,
    match_results: dict[int, dict[str, str]],
    used_third_groups: set[str],
) -> str:
    return _resolve_slot(slot_label, standings, match_results, used_third_groups)


def _knockout_prediction_row(
    row: object,
    standings: pd.DataFrame,
    match_results: dict[int, dict[str, str]],
    used_third_groups: set[str],
) -> dict[str, object]:
    match_id = int(getattr(row, "match_id"))
    predicted_home_team = _resolve_slot(
        getattr(row, "slot_home"),
        standings,
        match_results,
        used_third_groups,
    )
    predicted_away_team = _resolve_slot(
        getattr(row, "slot_away"),
        standings,
        match_results,
        used_third_groups,
    )

    seed = _stable_int(match_id, predicted_home_team, predicted_away_team)
    home_goals, away_goals = _score_prediction(match_id, predicted_home_team, predicted_away_team)
    penalties = seed % 7 == 0

    if penalties:
        away_goals = home_goals
        match_winner = "home" if seed % 2 == 0 else "away"
    elif home_goals == away_goals:
        if seed % 2 == 0:
            home_goals += 1
            match_winner = "home"
        else:
            away_goals += 1
            match_winner = "away"
    else:
        match_winner = _group_winner(home_goals, away_goals)

    winner_team = predicted_home_team if match_winner == "home" else predicted_away_team
    loser_team = predicted_away_team if match_winner == "home" else predicted_home_team
    match_results[match_id] = {"winner_team": winner_team, "loser_team": loser_team}

    return {
        **row._asdict(),
        "predicted_home_team": predicted_home_team,
        "predicted_away_team": predicted_away_team,
        "predicted_home_goals": home_goals,
        "predicted_away_goals": away_goals,
        **_match_totals(seed),
        "match_winner": match_winner,
        "penalties": penalties,
    }


def build_knockout_predictions(
    knockout_slots: pd.DataFrame,
    group_predictions: pd.DataFrame,
) -> pd.DataFrame:
    standings = build_group_standings(group_predictions)
    match_results: dict[int, dict[str, str]] = {}
    used_third_groups: set[str] = set()
    predictions = []

    for row in knockout_slots.sort_values("match_id").itertuples(index=False):
        predictions.append(
            _knockout_prediction_row(
                row=row,
                standings=standings,
                match_results=match_results,
                used_third_groups=used_third_groups,
            )
        )

    return pd.DataFrame(predictions)[[*knockout_slots.columns, *KNOCKOUT_PREDICTION_COLUMNS]]


def build_baseline_predictions(
    group_fixtures: pd.DataFrame,
    knockout_slots: pd.DataFrame,
) -> pd.DataFrame:
    group_predictions = build_group_predictions(group_fixtures)
    knockout_predictions = build_knockout_predictions(knockout_slots, group_predictions)

    group_combined = group_predictions.assign(
        competition_phase="group",
        predicted_home_team=group_predictions["home_team"],
        predicted_away_team=group_predictions["away_team"],
        match_winner=group_predictions["winning_team"],
        penalties=False,
        round=None,
        multiplier=1,
    )
    knockout_combined = knockout_predictions.assign(
        competition_phase="knockout",
        group=None,
        home_team=knockout_predictions["predicted_home_team"],
        away_team=knockout_predictions["predicted_away_team"],
        winning_team=None,
    )

    combined_columns = [
        "match_id",
        "competition_phase",
        "group",
        "round",
        "multiplier",
        "home_team",
        "away_team",
        "predicted_home_team",
        "predicted_away_team",
        "predicted_home_goals",
        "predicted_away_goals",
        "corners",
        "yellow_cards",
        "red_cards",
        "winning_team",
        "match_winner",
        "penalties",
    ]
    return pd.concat(
        [group_combined[combined_columns], knockout_combined[combined_columns]],
        ignore_index=True,
    ).sort_values("match_id")
