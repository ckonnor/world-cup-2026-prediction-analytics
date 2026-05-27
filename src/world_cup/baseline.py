from __future__ import annotations

import hashlib

import pandas as pd


def _stable_int(*parts: object) -> int:
    key = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def _prediction_row(
    match_id: object,
    home_team: str,
    away_team: str,
    competition_phase: str,
    group_letter: str | None = None,
    round_name: str | None = None,
    score_multiplier: float = 1.0,
) -> dict[str, object]:
    seed = _stable_int(match_id, home_team, away_team)
    home_goals = [0, 1, 1, 2, 2, 3][seed % 6]
    away_goals = [0, 0, 1, 1, 2, 2][(seed // 7) % 6]

    if competition_phase == "knockout" and home_goals == away_goals:
        home_goals += 1

    if home_goals > away_goals:
        predicted_result = home_team
    elif away_goals > home_goals:
        predicted_result = away_team
    else:
        predicted_result = "Draw"

    return {
        "match_id": match_id,
        "competition_phase": competition_phase,
        "group_letter": group_letter,
        "round_name": round_name,
        "score_multiplier": score_multiplier,
        "home_team": home_team,
        "away_team": away_team,
        "predicted_home_goals": home_goals,
        "predicted_away_goals": away_goals,
        "predicted_result": predicted_result,
        "predicted_home_corners": 4 + (seed % 5),
        "predicted_away_corners": 3 + ((seed // 11) % 5),
        "predicted_home_yellow_cards": 1 + ((seed // 13) % 4),
        "predicted_away_yellow_cards": 1 + ((seed // 17) % 4),
        "predicted_home_red_cards": 1 if seed % 97 == 0 else 0,
        "predicted_away_red_cards": 1 if seed % 89 == 0 else 0,
    }


def build_baseline_predictions(
    group_fixtures: pd.DataFrame,
    knockout_slots: pd.DataFrame,
) -> pd.DataFrame:
    predictions: list[dict[str, object]] = []

    for row in group_fixtures.itertuples(index=False):
        predictions.append(
            _prediction_row(
                match_id=getattr(row, "match_id"),
                home_team=getattr(row, "home_team"),
                away_team=getattr(row, "away_team"),
                competition_phase="group",
                group_letter=getattr(row, "group"),
                score_multiplier=1.0,
            )
        )

    for row in knockout_slots.itertuples(index=False):
        predictions.append(
            _prediction_row(
                match_id=getattr(row, "match_id"),
                home_team=getattr(row, "slot_home"),
                away_team=getattr(row, "slot_away"),
                competition_phase="knockout",
                round_name=getattr(row, "round"),
                score_multiplier=float(getattr(row, "multiplier")),
            )
        )

    return pd.DataFrame(predictions).sort_values("match_id")
