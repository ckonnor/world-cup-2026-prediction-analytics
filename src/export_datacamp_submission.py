from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from world_cup.paths import (
    MODEL_GROUP_PREDICTIONS_V2_PATH,
    MODEL_KNOCKOUT_PREDICTIONS_V2_PATH,
    MODEL_PREDICTIONS_V2_PATH,
    PROCESSED_DIR,
    SUBMISSION_GROUP_PREDICTIONS_PATH,
    SUBMISSION_KNOCKOUT_PREDICTIONS_PATH,
    SUBMISSION_PREDICTIONS_PATH,
    SUBMISSION_VALIDATION_PATH,
)


GROUP_COLUMNS = [
    "match_id",
    "group",
    "home_team",
    "away_team",
    "date_utc",
    "venue",
    "predicted_home_goals",
    "predicted_away_goals",
    "corners",
    "yellow_cards",
    "red_cards",
    "winning_team",
]

KNOCKOUT_COLUMNS = [
    "match_id",
    "round",
    "multiplier",
    "date_utc",
    "venue",
    "slot_home",
    "slot_away",
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

COMBINED_COLUMNS = [
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

INTEGER_COLUMNS = [
    "match_id",
    "predicted_home_goals",
    "predicted_away_goals",
    "corners",
    "yellow_cards",
    "red_cards",
]


@dataclass(frozen=True)
class SubmissionFrames:
    group: pd.DataFrame
    knockout: pd.DataFrame
    combined: pd.DataFrame


def _missing_columns(frame: pd.DataFrame, required_columns: Iterable[str]) -> list[str]:
    return [column for column in required_columns if column not in frame.columns]


def _outcome_from_score(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home"
    if away_goals > home_goals:
        return "away"
    return "draw"


def _validate_required_columns(
    frame: pd.DataFrame,
    required_columns: list[str],
    frame_name: str,
) -> list[str]:
    missing_columns = _missing_columns(frame, required_columns)
    if missing_columns:
        return [f"{frame_name} missing columns: {', '.join(missing_columns)}"]
    return []


def _validate_integer_columns(
    frame: pd.DataFrame,
    frame_name: str,
) -> list[str]:
    errors = []
    for column in [item for item in INTEGER_COLUMNS if item in frame.columns]:
        numeric_values = pd.to_numeric(frame[column], errors="coerce")
        if numeric_values.isna().any():
            errors.append(f"{frame_name}.{column} contains non-numeric values.")
            continue
        if not (numeric_values % 1 == 0).all():
            errors.append(f"{frame_name}.{column} contains non-integer values.")
        if column != "match_id" and (numeric_values < 0).any():
            errors.append(f"{frame_name}.{column} contains negative values.")
    return errors


def _validate_match_ids(
    frame: pd.DataFrame,
    expected_match_ids: set[int],
    frame_name: str,
) -> list[str]:
    errors = []
    numeric_match_ids = pd.to_numeric(frame["match_id"], errors="coerce")
    if numeric_match_ids.isna().any() or not (numeric_match_ids % 1 == 0).all():
        return [f"{frame_name}.match_id must contain integer IDs."]

    actual_match_ids = set(numeric_match_ids.astype(int))
    if actual_match_ids != expected_match_ids:
        missing = sorted(expected_match_ids - actual_match_ids)
        unexpected = sorted(actual_match_ids - expected_match_ids)
        if missing:
            errors.append(f"{frame_name} missing match IDs: {missing}")
        if unexpected:
            errors.append(f"{frame_name} unexpected match IDs: {unexpected}")
    if frame["match_id"].duplicated().any():
        errors.append(f"{frame_name} has duplicate match IDs.")
    return errors


def _validate_group_predictions(group: pd.DataFrame) -> list[str]:
    errors = []
    errors.extend(_validate_required_columns(group, GROUP_COLUMNS, "group_predictions"))
    if errors:
        return errors

    if len(group) != 72:
        errors.append(f"group_predictions has {len(group)} rows; expected 72.")
    errors.extend(_validate_match_ids(group, set(range(1, 73)), "group_predictions"))
    integer_errors = _validate_integer_columns(group, "group_predictions")
    errors.extend(integer_errors)

    if group[GROUP_COLUMNS].isna().any().any():
        errors.append("group_predictions contains null values in workbook columns.")
    if not set(group["winning_team"]).issubset({"home", "away", "draw"}):
        errors.append("group_predictions.winning_team contains invalid values.")
    if integer_errors:
        return errors

    score_outcomes = [
        _outcome_from_score(int(row.predicted_home_goals), int(row.predicted_away_goals))
        for row in group.itertuples(index=False)
    ]
    if (group["winning_team"].to_numpy() != pd.Series(score_outcomes).to_numpy()).any():
        errors.append("group_predictions.winning_team does not match predicted scores.")

    return errors


def _validate_knockout_predictions(knockout: pd.DataFrame) -> list[str]:
    errors = []
    errors.extend(
        _validate_required_columns(knockout, KNOCKOUT_COLUMNS, "knockout_predictions")
    )
    if errors:
        return errors

    if len(knockout) != 32:
        errors.append(f"knockout_predictions has {len(knockout)} rows; expected 32.")
    errors.extend(_validate_match_ids(knockout, set(range(73, 105)), "knockout_predictions"))
    integer_errors = _validate_integer_columns(knockout, "knockout_predictions")
    errors.extend(integer_errors)

    if knockout[KNOCKOUT_COLUMNS].isna().any().any():
        errors.append("knockout_predictions contains null values in workbook columns.")
    if not set(knockout["match_winner"]).issubset({"home", "away"}):
        errors.append("knockout_predictions.match_winner contains invalid values.")
    if integer_errors:
        return errors

    penalties = knockout["penalties"]
    if not penalties.map(type).eq(bool).all():
        errors.append("knockout_predictions.penalties must contain booleans.")

    tied_scores = knockout["predicted_home_goals"] == knockout["predicted_away_goals"]
    if (penalties != tied_scores).any():
        errors.append("knockout penalty flags must match tied predicted scores.")

    return errors


def _validate_combined_predictions(combined: pd.DataFrame) -> list[str]:
    errors = []
    errors.extend(_validate_required_columns(combined, COMBINED_COLUMNS, "combined_predictions"))
    if errors:
        return errors

    if len(combined) != 104:
        errors.append(f"combined_predictions has {len(combined)} rows; expected 104.")
    errors.extend(_validate_match_ids(combined, set(range(1, 105)), "combined_predictions"))
    expected_phase_counts = {"group": 72, "knockout": 32}
    actual_phase_counts = combined["competition_phase"].value_counts().to_dict()
    if actual_phase_counts != expected_phase_counts:
        errors.append(
            "combined_predictions phase counts were "
            f"{actual_phase_counts}; expected {expected_phase_counts}."
        )
    return errors


def validate_submission_frames(frames: SubmissionFrames) -> dict[str, object]:
    errors = [
        *_validate_group_predictions(frames.group),
        *_validate_knockout_predictions(frames.knockout),
        *_validate_combined_predictions(frames.combined),
    ]
    group_distribution = (
        frames.group["winning_team"].value_counts().items()
        if "winning_team" in frames.group.columns
        else []
    )
    knockout_penalties = (
        frames.knockout["penalties"].value_counts().items()
        if "penalties" in frames.knockout.columns
        else []
    )
    return {
        "valid": not errors,
        "errors": errors,
        "row_counts": {
            "group_predictions": int(len(frames.group)),
            "knockout_predictions": int(len(frames.knockout)),
            "combined_predictions": int(len(frames.combined)),
        },
        "group_result_distribution": {
            key: int(value) for key, value in group_distribution
        },
        "knockout_penalties": {
            str(key): int(value) for key, value in knockout_penalties
        },
    }


def load_model_frames() -> SubmissionFrames:
    input_paths = [
        MODEL_GROUP_PREDICTIONS_V2_PATH,
        MODEL_KNOCKOUT_PREDICTIONS_V2_PATH,
        MODEL_PREDICTIONS_V2_PATH,
    ]
    missing_paths = [path for path in input_paths if not path.exists()]
    if missing_paths:
        missing_text = "\n".join(f"- {path}" for path in missing_paths)
        raise FileNotFoundError(
            "Missing model prediction artifacts. Run src/train_model.py first:\n"
            f"{missing_text}"
        )

    return SubmissionFrames(
        group=pd.read_csv(MODEL_GROUP_PREDICTIONS_V2_PATH),
        knockout=pd.read_csv(MODEL_KNOCKOUT_PREDICTIONS_V2_PATH),
        combined=pd.read_csv(MODEL_PREDICTIONS_V2_PATH),
    )


def _finalize_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    finalized = frame[columns].copy()
    for column in [item for item in INTEGER_COLUMNS if item in finalized.columns]:
        finalized[column] = finalized[column].astype(int)
    if "penalties" in finalized.columns:
        finalized["penalties"] = finalized["penalties"].astype(bool)
    return finalized


def export_submission_files() -> dict[str, object]:
    frames = load_model_frames()
    validation = validate_submission_frames(frames)
    if not validation["valid"]:
        raise ValueError(
            "Submission validation failed:\n"
            + "\n".join(f"- {error}" for error in validation["errors"])
        )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    group_submission = _finalize_columns(frames.group, GROUP_COLUMNS)
    knockout_submission = _finalize_columns(frames.knockout, KNOCKOUT_COLUMNS)
    combined_submission = _finalize_columns(frames.combined, COMBINED_COLUMNS)

    group_submission.to_csv(SUBMISSION_GROUP_PREDICTIONS_PATH, index=False)
    knockout_submission.to_csv(SUBMISSION_KNOCKOUT_PREDICTIONS_PATH, index=False)
    combined_submission.to_csv(SUBMISSION_PREDICTIONS_PATH, index=False)
    SUBMISSION_VALIDATION_PATH.write_text(
        json.dumps(validation, indent=2),
        encoding="utf-8",
    )
    return validation


def main() -> None:
    validation = export_submission_files()
    print(f"Wrote group submission to {SUBMISSION_GROUP_PREDICTIONS_PATH}")
    print(f"Wrote knockout submission to {SUBMISSION_KNOCKOUT_PREDICTIONS_PATH}")
    print(f"Wrote combined submission to {SUBMISSION_PREDICTIONS_PATH}")
    print(f"Wrote validation summary to {SUBMISSION_VALIDATION_PATH}")
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
