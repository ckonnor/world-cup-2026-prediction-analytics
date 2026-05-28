from __future__ import annotations

import pandas as pd

from export_datacamp_submission import (
    GROUP_COLUMNS,
    KNOCKOUT_COLUMNS,
    SubmissionFrames,
    validate_submission_frames,
)


def _valid_group_frame() -> pd.DataFrame:
    rows = []
    for match_id in range(1, 73):
        rows.append(
            {
                "match_id": match_id,
                "group": "A",
                "home_team": f"Home {match_id}",
                "away_team": f"Away {match_id}",
                "date_utc": "2026-06-11T19:00:00Z",
                "venue": "Venue",
                "predicted_home_goals": 1,
                "predicted_away_goals": 0,
                "corners": 9,
                "yellow_cards": 4,
                "red_cards": 0,
                "winning_team": "home",
            }
        )
    return pd.DataFrame(rows, columns=GROUP_COLUMNS)


def _valid_knockout_frame() -> pd.DataFrame:
    rows = []
    for match_id in range(73, 105):
        rows.append(
            {
                "match_id": match_id,
                "round": "Round of 32",
                "multiplier": 1,
                "date_utc": "2026-06-28T19:00:00Z",
                "venue": "Venue",
                "slot_home": "Winner Group A",
                "slot_away": "Runner-up Group B",
                "predicted_home_team": f"Home {match_id}",
                "predicted_away_team": f"Away {match_id}",
                "predicted_home_goals": 1,
                "predicted_away_goals": 0,
                "corners": 9,
                "yellow_cards": 4,
                "red_cards": 0,
                "match_winner": "home",
                "penalties": False,
            }
        )
    return pd.DataFrame(rows, columns=KNOCKOUT_COLUMNS)


def _valid_combined_frame(group: pd.DataFrame, knockout: pd.DataFrame) -> pd.DataFrame:
    group_combined = group.assign(
        competition_phase="group",
        round=None,
        multiplier=1,
        predicted_home_team=group["home_team"],
        predicted_away_team=group["away_team"],
        match_winner=group["winning_team"],
        penalties=False,
    )
    knockout_combined = knockout.assign(
        competition_phase="knockout",
        group=None,
        home_team=knockout["predicted_home_team"],
        away_team=knockout["predicted_away_team"],
        winning_team=None,
    )
    columns = [
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
        [group_combined[columns], knockout_combined[columns]],
        ignore_index=True,
    )


def test_validate_submission_frames_accepts_valid_shapes() -> None:
    group = _valid_group_frame()
    knockout = _valid_knockout_frame()
    combined = _valid_combined_frame(group, knockout)

    validation = validate_submission_frames(
        SubmissionFrames(group=group, knockout=knockout, combined=combined)
    )

    assert validation["valid"] is True
    assert validation["errors"] == []


def test_validate_submission_frames_rejects_score_outcome_mismatch() -> None:
    group = _valid_group_frame()
    knockout = _valid_knockout_frame()
    combined = _valid_combined_frame(group, knockout)
    group.loc[0, "winning_team"] = "away"

    validation = validate_submission_frames(
        SubmissionFrames(group=group, knockout=knockout, combined=combined)
    )

    assert validation["valid"] is False
    assert any("winning_team does not match" in error for error in validation["errors"])


def test_validate_submission_frames_rejects_penalty_mismatch() -> None:
    group = _valid_group_frame()
    knockout = _valid_knockout_frame()
    combined = _valid_combined_frame(group, knockout)
    knockout.loc[0, "penalties"] = True

    validation = validate_submission_frames(
        SubmissionFrames(group=group, knockout=knockout, combined=combined)
    )

    assert validation["valid"] is False
    assert any("penalty flags" in error for error in validation["errors"])


def test_validate_submission_frames_rejects_invalid_match_ids_without_crashing() -> None:
    group = _valid_group_frame()
    knockout = _valid_knockout_frame()
    combined = _valid_combined_frame(group, knockout)
    group["match_id"] = group["match_id"].astype(object)
    group.loc[0, "match_id"] = "not-a-match"

    validation = validate_submission_frames(
        SubmissionFrames(group=group, knockout=knockout, combined=combined)
    )

    assert validation["valid"] is False
    assert any("match_id must contain integer IDs" in error for error in validation["errors"])


def test_validate_submission_frames_reports_missing_columns_without_crashing() -> None:
    group = _valid_group_frame().drop(columns=["winning_team"])
    knockout = _valid_knockout_frame()
    combined = _valid_combined_frame(_valid_group_frame(), knockout)

    validation = validate_submission_frames(
        SubmissionFrames(group=group, knockout=knockout, combined=combined)
    )

    assert validation["valid"] is False
    assert any("missing columns" in error for error in validation["errors"])
