from __future__ import annotations

import json
import math
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

import duckdb
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, PoissonRegressor
from sklearn.metrics import accuracy_score, mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from world_cup.baseline import build_group_standings, resolve_knockout_slot
from world_cup.paths import (
    DUCKDB_PATH,
    MODEL_GROUP_PREDICTIONS_V2_PATH,
    MODEL_KNOCKOUT_PREDICTIONS_V2_PATH,
    MODEL_METRICS_V2_PATH,
    MODEL_PREDICTIONS_V2_PATH,
    MODEL_TEAM_FEATURES_V2_PATH,
    MODEL_TOURNAMENT_SIMULATION_V2_PATH,
    PROCESSED_DIR,
)


BASE_FEATURE_COLUMNS = [
    "neutral",
    "home_prior_10_adjusted_points_per_match",
    "away_prior_10_adjusted_points_per_match",
    "home_prior_10_adjusted_goal_diff_per_match",
    "away_prior_10_adjusted_goal_diff_per_match",
    "home_prior_10_goals_for_per_match",
    "away_prior_10_goals_for_per_match",
    "home_prior_10_goals_against_per_match",
    "away_prior_10_goals_against_per_match",
    "prior_10_adjusted_points_per_match_diff",
    "prior_10_adjusted_goal_diff_per_match_diff",
    "prior_10_goals_for_per_match_diff",
    "prior_10_goals_against_per_match_diff",
]

ELO_FEATURE_COLUMNS = [
    "home_pre_match_elo",
    "away_pre_match_elo",
    "pre_match_elo_diff",
    "home_elo_expected_result",
]

FIFA_RANKING_FEATURE_COLUMNS = [
    "home_fifa_rank",
    "away_fifa_rank",
    "home_fifa_points",
    "away_fifa_points",
    "fifa_rank_diff",
    "fifa_points_diff",
]

FEATURE_COLUMNS = [
    *BASE_FEATURE_COLUMNS,
    *FIFA_RANKING_FEATURE_COLUMNS,
    *ELO_FEATURE_COLUMNS,
]
EXTERNAL_OUTCOME_FEATURE_COLUMNS = [
    "external_home_elo",
    "external_away_elo",
    "external_elo_diff",
    "external_home_avg_overall",
    "external_home_max_overall",
    "external_home_avg_attack",
    "external_home_avg_defense",
    "external_home_avg_pace",
    "external_home_avg_shooting",
    "external_home_avg_passing",
    "external_away_avg_overall",
    "external_away_max_overall",
    "external_away_avg_attack",
    "external_away_avg_defense",
    "external_away_avg_pace",
    "external_away_avg_shooting",
    "external_away_avg_passing",
    "external_overall_diff",
    "external_attack_diff",
    "external_defense_diff",
    "external_home_form_scored",
    "external_home_form_conceded",
    "external_home_form_win_rate",
    "external_away_form_scored",
    "external_away_form_conceded",
    "external_away_form_win_rate",
    "has_external_match_features",
]
OUTCOME_FEATURE_COLUMNS = [
    *FEATURE_COLUMNS,
    *EXTERNAL_OUTCOME_FEATURE_COLUMNS,
]

HOST_TEAMS = {"Canada", "Mexico", "United States"}
TEAM_NAME_ALIASES = {
    "usa": "United States",
    "cabo verde": "Cape Verde",
    "cote d'ivoire": "Ivory Coast",
    "cote divoire": "Ivory Coast",
    "czechia": "Czech Republic",
    "turkiye": "Turkey",
    "congo dr": "DR Congo",
    "bosnia-herzegovina": "Bosnia and Herzegovina",
    "cape verde islands": "Cape Verde",
    "ir iran": "Iran",
    "korea republic": "South Korea",
}
DEFAULT_ELO = 1500.0
HOME_ADVANTAGE_ELO = 60.0
SQUAD_GOAL_ADJUSTMENT_CAP = 0.35
SQUAD_OVERALL_WEIGHT = 0.06
SQUAD_ATTACK_DEFENSE_WEIGHT = 0.07
SQUAD_EXPERIENCE_WEIGHT = 0.03
DEFAULT_TOTAL_CORNERS = 9.0
DEFAULT_TOTAL_YELLOW_CARDS = 4.0
DEFAULT_TOTAL_RED_CARDS = 0.15
KNOCKOUT_YELLOW_CARD_ADJUSTMENTS = {
    "Round of 32": 0.20,
    "Round of 16": 0.25,
    "Quarter-final": 0.35,
    "Semi-final": 0.45,
    "Third-place playoff": 0.15,
    "Final": 0.50,
}
KNOCKOUT_RED_CARD_ADJUSTMENT_FACTOR = 0.08
MIN_CALIBRATED_DRAW_RATE = 0.09
TOURNAMENT_CALIBRATION_START = pd.Timestamp("2018-01-01")
TOURNAMENT_FOCUSED_TOURNAMENTS = {
    "AFC Asian Cup",
    "AFC Asian Cup qualification",
    "African Cup of Nations",
    "African Cup of Nations qualification",
    "CONCACAF Nations League",
    "CONCACAF Nations League qualification",
    "Confederations Cup",
    "Copa América",
    "FIFA World Cup",
    "FIFA World Cup qualification",
    "Gold Cup",
    "Oceania Nations Cup",
    "Oceania Nations Cup qualification",
    "UEFA Euro",
    "UEFA Euro qualification",
    "UEFA Nations League",
}
SCORELINE_MAX_GOALS = 8
SCORELINE_BLEND_WEIGHT_CANDIDATES = np.arange(0.0, 1.01, 0.05)
MIN_OUTCOME_PROBABILITY = 1e-12
TOURNAMENT_SIMULATION_RUNS = 5000
TOURNAMENT_SIMULATION_RANDOM_SEED = 202606
MODEL_METRIC_TARGETS = {
    "rounded_scoreline_outcome_accuracy": {
        "direction": "higher",
        "guardrail": 0.545,
        "target": 0.57,
        "stretch": 0.60,
        "metric_path": ("holdout", "rounded_match_outcome_accuracy"),
    },
    "direct_outcome_accuracy": {
        "direction": "higher",
        "guardrail": 0.58,
        "target": 0.62,
        "stretch": 0.65,
        "metric_path": ("outcome_holdout", "accuracy"),
    },
    "reconciled_scoreline_exact_accuracy": {
        "direction": "higher",
        "guardrail": 0.10,
        "target": 0.12,
        "stretch": 0.14,
        "metric_path": ("reconciled_holdout", "exact_score_accuracy"),
    },
    "average_goals_mae": {
        "direction": "lower",
        "guardrail": 0.95,
        "target": 0.90,
        "stretch": 0.86,
        "metric_path": ("holdout", "average_goals_mae"),
    },
}


@dataclass(frozen=True)
class ModelSpec:
    name: str
    factory: Callable[[], object]


@dataclass(frozen=True)
class TrainedGoalModels:
    home_model: object
    away_model: object
    outcome_model: object
    feature_medians: pd.Series
    outcome_feature_medians: pd.Series
    current_elo_ratings: dict[str, float]
    current_adjusted_team_features: dict[str, dict[str, float]]
    selected_model_name: str
    selected_outcome_model_name: str
    outcome_classes: np.ndarray
    draw_probability_threshold: float
    scoreline_outcome_blend_weight: float


def _normalise_text(value: object) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value))
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.casefold().split())


def canonical_team_name(team_name: object) -> str:
    raw_name = str(team_name)
    return TEAM_NAME_ALIASES.get(_normalise_text(raw_name), raw_name)


def _load_table(table_name: str) -> pd.DataFrame:
    if not DUCKDB_PATH.exists():
        raise FileNotFoundError(
            f"{DUCKDB_PATH} does not exist. Run dbt build before training the model."
        )

    with duckdb.connect(str(DUCKDB_PATH), read_only=True) as con:
        return con.execute(f"select * from {table_name}").fetchdf()


def _elo_expected_score(home_elo: float, away_elo: float, neutral: bool) -> float:
    home_adjusted = home_elo + (0.0 if neutral else HOME_ADVANTAGE_ELO)
    return 1.0 / (1.0 + 10 ** ((away_elo - home_adjusted) / 400.0))


def _goal_difference_multiplier(home_score: int, away_score: int) -> float:
    goal_difference = abs(home_score - away_score)
    if goal_difference <= 1:
        return 1.0
    return 1.0 + math.log(goal_difference)


def _k_factor(tournament: str) -> float:
    tournament_key = _normalise_text(tournament)
    if tournament_key == "fifa world cup":
        return 60.0
    if "qualifi" in tournament_key:
        return 35.0
    if tournament_key in {
        "afc asian cup",
        "african cup of nations",
        "copa america",
        "concacaf gold cup",
        "fifa confederations cup",
        "oceania nations cup",
        "uefa euro",
    }:
        return 50.0
    if tournament_key == "friendly":
        return 20.0
    return 30.0


def build_elo_features(results: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    ratings: dict[str, float] = {}
    rows: list[dict[str, float | str]] = []

    sorted_results = results.copy()
    sorted_results["match_date"] = pd.to_datetime(sorted_results["match_date"])
    sorted_results = sorted_results.sort_values(["match_date", "result_id"])

    for row in sorted_results.itertuples(index=False):
        home_team = canonical_team_name(row.home_team)
        away_team = canonical_team_name(row.away_team)
        home_elo = ratings.get(home_team, DEFAULT_ELO)
        away_elo = ratings.get(away_team, DEFAULT_ELO)
        neutral = bool(row.neutral)
        expected_home = _elo_expected_score(home_elo, away_elo, neutral)

        if row.home_score > row.away_score:
            actual_home = 1.0
        elif row.home_score < row.away_score:
            actual_home = 0.0
        else:
            actual_home = 0.5

        rows.append(
            {
                "result_id": row.result_id,
                "home_pre_match_elo": home_elo,
                "away_pre_match_elo": away_elo,
                "pre_match_elo_diff": home_elo - away_elo,
                "home_elo_expected_result": expected_home,
            }
        )

        rating_change = (
            _k_factor(str(row.tournament))
            * _goal_difference_multiplier(int(row.home_score), int(row.away_score))
            * (actual_home - expected_home)
        )
        ratings[home_team] = home_elo + rating_change
        ratings[away_team] = away_elo - rating_change

    return pd.DataFrame(rows), ratings


def _actual_result_score(goals_for: int, goals_against: int) -> float:
    if goals_for > goals_against:
        return 1.0
    if goals_for < goals_against:
        return 0.0
    return 0.5


def build_opponent_adjusted_form_features(
    results: pd.DataFrame,
    elo_features: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, dict[str, float]]]:
    matches = results.merge(elo_features, on="result_id", how="inner").copy()
    matches["match_date"] = pd.to_datetime(matches["match_date"])
    matches = matches.sort_values(["match_date", "result_id"])

    team_rows = []
    for row in matches.itertuples(index=False):
        home_team = canonical_team_name(row.home_team)
        away_team = canonical_team_name(row.away_team)
        expected_home = float(row.home_elo_expected_result)
        expected_away = 1.0 - expected_home
        home_actual_score = _actual_result_score(int(row.home_score), int(row.away_score))
        away_actual_score = 1.0 - home_actual_score
        home_goal_difference = int(row.home_score) - int(row.away_score)
        away_goal_difference = -home_goal_difference
        home_expected_goal_difference = 2.0 * (expected_home - 0.5)
        away_expected_goal_difference = 2.0 * (expected_away - 0.5)

        team_rows.extend(
            [
                {
                    "result_id": row.result_id,
                    "match_date": row.match_date,
                    "team_name": home_team,
                    "is_home_team": True,
                    "adjusted_points": (3.0 * home_actual_score) - (3.0 * expected_home),
                    "adjusted_goal_diff": home_goal_difference
                    - home_expected_goal_difference,
                },
                {
                    "result_id": row.result_id,
                    "match_date": row.match_date,
                    "team_name": away_team,
                    "is_home_team": False,
                    "adjusted_points": (3.0 * away_actual_score) - (3.0 * expected_away),
                    "adjusted_goal_diff": away_goal_difference
                    - away_expected_goal_difference,
                },
            ]
        )

    team_history = pd.DataFrame(team_rows).sort_values(["team_name", "match_date", "result_id"])
    grouped = team_history.groupby("team_name", group_keys=False)
    team_history["prior_10_adjusted_points_per_match"] = grouped["adjusted_points"].transform(
        lambda series: series.shift(1).rolling(10, min_periods=1).mean()
    )
    team_history["prior_10_adjusted_goal_diff_per_match"] = grouped[
        "adjusted_goal_diff"
    ].transform(lambda series: series.shift(1).rolling(10, min_periods=1).mean())

    home_form = team_history[team_history["is_home_team"]].rename(
        columns={
            "prior_10_adjusted_points_per_match": "home_prior_10_adjusted_points_per_match",
            "prior_10_adjusted_goal_diff_per_match": (
                "home_prior_10_adjusted_goal_diff_per_match"
            ),
        }
    )
    away_form = team_history[~team_history["is_home_team"]].rename(
        columns={
            "prior_10_adjusted_points_per_match": "away_prior_10_adjusted_points_per_match",
            "prior_10_adjusted_goal_diff_per_match": (
                "away_prior_10_adjusted_goal_diff_per_match"
            ),
        }
    )
    adjusted_match_features = home_form[
        [
            "result_id",
            "home_prior_10_adjusted_points_per_match",
            "home_prior_10_adjusted_goal_diff_per_match",
        ]
    ].merge(
        away_form[
            [
                "result_id",
                "away_prior_10_adjusted_points_per_match",
                "away_prior_10_adjusted_goal_diff_per_match",
            ]
        ],
        on="result_id",
        how="inner",
    )
    adjusted_match_features["prior_10_adjusted_points_per_match_diff"] = (
        adjusted_match_features["home_prior_10_adjusted_points_per_match"]
        - adjusted_match_features["away_prior_10_adjusted_points_per_match"]
    )
    adjusted_match_features["prior_10_adjusted_goal_diff_per_match_diff"] = (
        adjusted_match_features["home_prior_10_adjusted_goal_diff_per_match"]
        - adjusted_match_features["away_prior_10_adjusted_goal_diff_per_match"]
    )

    current_features = {}
    for team_name, team_frame in team_history.groupby("team_name"):
        latest = team_frame.tail(10)
        current_features[_normalise_text(team_name)] = {
            "last_10_adjusted_points_per_match": float(latest["adjusted_points"].mean()),
            "last_10_adjusted_goal_diff_per_match": float(latest["adjusted_goal_diff"].mean()),
        }

    return adjusted_match_features, current_features


def _prepare_training_features(data: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    features = data[feature_columns].copy()
    features["neutral"] = features["neutral"].astype(int)
    return features


def _is_tournament_focused_match(data: pd.DataFrame) -> pd.Series:
    return data["tournament"].isin(TOURNAMENT_FOCUSED_TOURNAMENTS)


def _tournament_calibration_mask(
    data: pd.DataFrame,
    holdout_start: pd.Timestamp,
) -> pd.Series:
    return (
        (data["match_date"] >= TOURNAMENT_CALIBRATION_START)
        & (data["match_date"] < holdout_start)
        & _is_tournament_focused_match(data)
    )


def _model_specs() -> list[ModelSpec]:
    return [
        ModelSpec(
            name="poisson_regression",
            factory=lambda: Pipeline(
                steps=[
                    ("scale", StandardScaler()),
                    ("poisson", PoissonRegressor(alpha=0.05, max_iter=1000)),
                ]
            ),
        ),
        ModelSpec(
            name="hist_gradient_boosting_poisson",
            factory=lambda: HistGradientBoostingRegressor(
                loss="poisson",
                learning_rate=0.04,
                max_iter=300,
                max_leaf_nodes=15,
                min_samples_leaf=40,
                l2_regularization=0.1,
                random_state=42,
            ),
        ),
    ]


def _outcome_model_specs() -> list[ModelSpec]:
    return [
        ModelSpec(
            name="multinomial_logistic_regression",
            factory=lambda: Pipeline(
                steps=[
                    ("scale", StandardScaler()),
                    (
                        "logistic",
                        LogisticRegression(C=0.8, max_iter=1000),
                    ),
                ]
            ),
        ),
        ModelSpec(
            name="hist_gradient_boosting_classifier",
            factory=lambda: HistGradientBoostingClassifier(
                learning_rate=0.04,
                max_iter=250,
                max_leaf_nodes=15,
                min_samples_leaf=40,
                l2_regularization=0.1,
                random_state=42,
            ),
        ),
    ]


def _rounded_goals(predictions: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(predictions), 0, 8).astype(int)


def _poisson_log_probability(goals: int, expected_goals: float) -> float:
    expected_goals = max(float(expected_goals), 0.05)
    return -expected_goals + goals * math.log(expected_goals) - math.lgamma(goals + 1)


def outcome_from_scores(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home"
    if away_goals > home_goals:
        return "away"
    return "draw"


def outcome_from_probabilities(
    probabilities: np.ndarray,
    classes: np.ndarray,
    draw_probability_threshold: float,
) -> str:
    class_indexes = {class_name: index for index, class_name in enumerate(classes)}
    draw_probability = probabilities[class_indexes["draw"]]
    if draw_probability >= draw_probability_threshold:
        return "draw"
    return (
        "home"
        if probabilities[class_indexes["home"]] >= probabilities[class_indexes["away"]]
        else "away"
    )


def _outcomes_from_probabilities(
    probabilities: np.ndarray,
    classes: np.ndarray,
    draw_probability_threshold: float,
) -> np.ndarray:
    return np.array(
        [
            outcome_from_probabilities(row, classes, draw_probability_threshold)
            for row in probabilities
        ]
    )


def _outcome_probability_lookup(
    probabilities: np.ndarray,
    classes: np.ndarray,
) -> dict[str, float]:
    return {
        str(class_name): max(float(probabilities[index]), MIN_OUTCOME_PROBABILITY)
        for index, class_name in enumerate(classes)
    }


def _select_blended_scoreline(
    home_expected_goals: float,
    away_expected_goals: float,
    outcome_probabilities: np.ndarray,
    classes: np.ndarray,
    outcome_blend_weight: float,
) -> tuple[int, int]:
    rounded_home = int(_rounded_goals(np.array([home_expected_goals]))[0])
    rounded_away = int(_rounded_goals(np.array([away_expected_goals]))[0])
    outcome_probability_by_class = _outcome_probability_lookup(outcome_probabilities, classes)
    outcome_blend_weight = float(np.clip(outcome_blend_weight, 0.0, 1.0))
    goal_blend_weight = 1.0 - outcome_blend_weight

    candidates = []
    for home_goals in range(0, SCORELINE_MAX_GOALS + 1):
        for away_goals in range(0, SCORELINE_MAX_GOALS + 1):
            outcome = outcome_from_scores(home_goals, away_goals)
            scoreline_log_probability = _poisson_log_probability(
                home_goals,
                home_expected_goals,
            ) + _poisson_log_probability(
                away_goals,
                away_expected_goals,
            )
            outcome_log_probability = math.log(outcome_probability_by_class[outcome])
            blended_log_probability = (
                goal_blend_weight * scoreline_log_probability
                + outcome_blend_weight * outcome_log_probability
            )
            squared_error = (
                (home_goals - home_expected_goals) ** 2
                + (away_goals - away_expected_goals) ** 2
            )
            total_goal_distance = abs(
                (home_goals + away_goals) - (rounded_home + rounded_away)
            )
            candidates.append(
                (
                    blended_log_probability,
                    scoreline_log_probability,
                    -squared_error,
                    -total_goal_distance,
                    home_goals,
                    away_goals,
                )
            )

    _, _, _, _, home_goals, away_goals = max(candidates)
    return int(home_goals), int(away_goals)


def _scoreline_probability_grid(
    home_expected_goals: float,
    away_expected_goals: float,
    outcome_probabilities: np.ndarray,
    classes: np.ndarray,
    outcome_blend_weight: float,
) -> pd.DataFrame:
    outcome_probability_by_class = _outcome_probability_lookup(outcome_probabilities, classes)
    outcome_blend_weight = float(np.clip(outcome_blend_weight, 0.0, 1.0))
    goal_blend_weight = 1.0 - outcome_blend_weight
    rows = []
    log_probabilities = []

    for home_goals in range(0, SCORELINE_MAX_GOALS + 1):
        for away_goals in range(0, SCORELINE_MAX_GOALS + 1):
            outcome = outcome_from_scores(home_goals, away_goals)
            scoreline_log_probability = _poisson_log_probability(
                home_goals,
                home_expected_goals,
            ) + _poisson_log_probability(
                away_goals,
                away_expected_goals,
            )
            outcome_log_probability = math.log(outcome_probability_by_class[outcome])
            blended_log_probability = (
                goal_blend_weight * scoreline_log_probability
                + outcome_blend_weight * outcome_log_probability
            )
            rows.append(
                {
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                    "outcome": outcome,
                }
            )
            log_probabilities.append(blended_log_probability)

    log_probability_array = np.array(log_probabilities)
    probability_array = np.exp(log_probability_array - log_probability_array.max())
    probability_array = probability_array / probability_array.sum()
    grid = pd.DataFrame(rows)
    grid["probability"] = probability_array
    return grid


def _score_predictions(
    frame: pd.DataFrame,
    home_predictions: np.ndarray,
    away_predictions: np.ndarray,
) -> dict[str, float]:
    predicted_home_goals = _rounded_goals(home_predictions)
    predicted_away_goals = _rounded_goals(away_predictions)
    actual_home_goals = frame["home_score"].to_numpy()
    actual_away_goals = frame["away_score"].to_numpy()

    predicted_outcomes = [
        outcome_from_scores(int(home), int(away))
        for home, away in zip(predicted_home_goals, predicted_away_goals)
    ]
    actual_outcomes = frame["match_outcome"].tolist()

    return {
        "rows": int(len(frame)),
        "home_goals_mae": float(mean_absolute_error(actual_home_goals, home_predictions)),
        "away_goals_mae": float(mean_absolute_error(actual_away_goals, away_predictions)),
        "average_goals_mae": float(
            (
                mean_absolute_error(actual_home_goals, home_predictions)
                + mean_absolute_error(actual_away_goals, away_predictions)
            )
            / 2.0
        ),
        "rounded_exact_score_accuracy": float(
            np.mean(
                (predicted_home_goals == actual_home_goals)
                & (predicted_away_goals == actual_away_goals)
            )
        ),
        "rounded_match_outcome_accuracy": float(
            np.mean(np.array(predicted_outcomes) == np.array(actual_outcomes))
        ),
    }


def _fit_goal_models(
    spec: ModelSpec,
    frame: pd.DataFrame,
) -> tuple[object, object]:
    features = _prepare_training_features(frame, FEATURE_COLUMNS)
    home_model = spec.factory()
    away_model = spec.factory()
    home_model.fit(features, frame["home_score"])
    away_model.fit(features, frame["away_score"])
    return home_model, away_model


def _score_goal_models(
    frame: pd.DataFrame,
    home_model: object,
    away_model: object,
) -> dict[str, float]:
    features = _prepare_training_features(frame, FEATURE_COLUMNS)
    return _score_predictions(
        frame,
        home_model.predict(features),
        away_model.predict(features),
    )


def _fit_and_score_spec(
    spec: ModelSpec,
    fitting: pd.DataFrame,
    calibration: pd.DataFrame,
    holdout: pd.DataFrame,
) -> tuple[object, object, dict[str, object]]:
    home_model, away_model = _fit_goal_models(spec, fitting)

    metrics = {
        "model_type": spec.name,
        "fitting": _score_goal_models(fitting, home_model, away_model),
        "calibration": _score_goal_models(calibration, home_model, away_model),
        "holdout": _score_goal_models(holdout, home_model, away_model),
    }
    return home_model, away_model, metrics


def _best_draw_probability_threshold(
    actual_outcomes: pd.Series,
    probabilities: np.ndarray,
    classes: np.ndarray,
) -> float:
    candidate_thresholds = np.arange(0.20, 0.61, 0.01)
    scored_thresholds = []
    for threshold in candidate_thresholds:
        predictions = _outcomes_from_probabilities(probabilities, classes, float(threshold))
        draw_rate = float(np.mean(predictions == "draw"))
        scored_thresholds.append(
            (
                accuracy_score(actual_outcomes, predictions),
                draw_rate,
                float(threshold),
            )
        )

    calibrated_thresholds = [
        item for item in scored_thresholds if item[1] >= MIN_CALIBRATED_DRAW_RATE
    ]
    if calibrated_thresholds:
        return max(calibrated_thresholds, key=lambda item: (item[0], item[2]))[2]

    return max(scored_thresholds, key=lambda item: (item[0], item[2]))[2]


def _score_outcome_predictions(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    classes: np.ndarray,
    draw_probability_threshold: float,
) -> dict[str, object]:
    predictions = _outcomes_from_probabilities(
        probabilities,
        classes,
        draw_probability_threshold,
    )
    return {
        "rows": int(len(frame)),
        "accuracy": float(accuracy_score(frame["match_outcome"], predictions)),
        "actual_distribution": {
            key: float(value)
            for key, value in frame["match_outcome"].value_counts(normalize=True).items()
        },
        "predicted_distribution": {
            key: float(value)
            for key, value in pd.Series(predictions).value_counts(normalize=True).items()
        },
    }


def _score_reconciled_predictions(
    frame: pd.DataFrame,
    home_predictions: np.ndarray,
    away_predictions: np.ndarray,
    outcome_probabilities: np.ndarray,
    classes: np.ndarray,
    scoreline_outcome_blend_weight: float,
) -> dict[str, object]:
    reconciled_scores = [
        _select_blended_scoreline(
            float(home),
            float(away),
            probabilities,
            classes,
            scoreline_outcome_blend_weight,
        )
        for home, away, probabilities in zip(
            home_predictions,
            away_predictions,
            outcome_probabilities,
        )
    ]
    predicted_home_goals = np.array([score[0] for score in reconciled_scores])
    predicted_away_goals = np.array([score[1] for score in reconciled_scores])
    predicted_outcomes = np.array(
        [
            outcome_from_scores(int(home), int(away))
            for home, away in zip(predicted_home_goals, predicted_away_goals)
        ]
    )
    actual_home_goals = frame["home_score"].to_numpy()
    actual_away_goals = frame["away_score"].to_numpy()

    return {
        "rows": int(len(frame)),
        "scoreline_outcome_blend_weight": float(scoreline_outcome_blend_weight),
        "exact_score_accuracy": float(
            np.mean(
                (predicted_home_goals == actual_home_goals)
                & (predicted_away_goals == actual_away_goals)
            )
        ),
        "match_outcome_accuracy": float(
            accuracy_score(frame["match_outcome"], predicted_outcomes)
        ),
        "predicted_distribution": {
            key: float(value)
            for key, value in pd.Series(predicted_outcomes).value_counts(normalize=True).items()
        },
    }


def _best_scoreline_outcome_blend_weight(
    frame: pd.DataFrame,
    home_predictions: np.ndarray,
    away_predictions: np.ndarray,
    outcome_probabilities: np.ndarray,
    classes: np.ndarray,
) -> tuple[float, list[dict[str, float]]]:
    scored_weights = []
    for weight in SCORELINE_BLEND_WEIGHT_CANDIDATES:
        metrics = _score_reconciled_predictions(
            frame,
            home_predictions,
            away_predictions,
            outcome_probabilities,
            classes,
            float(weight),
        )
        predicted_draw_rate = float(metrics["predicted_distribution"].get("draw", 0.0))
        scored_weights.append(
            {
                "scoreline_outcome_blend_weight": float(weight),
                "exact_score_accuracy": float(metrics["exact_score_accuracy"]),
                "match_outcome_accuracy": float(metrics["match_outcome_accuracy"]),
                "predicted_draw_rate": predicted_draw_rate,
            }
        )

    calibrated_weights = [
        item
        for item in scored_weights
        if item["predicted_draw_rate"] >= MIN_CALIBRATED_DRAW_RATE
    ]
    eligible_weights = calibrated_weights or scored_weights
    selected_weight = max(
        eligible_weights,
        key=lambda item: (
            item["match_outcome_accuracy"],
            item["exact_score_accuracy"],
            -item["scoreline_outcome_blend_weight"],
        ),
    )
    return float(selected_weight["scoreline_outcome_blend_weight"]), scored_weights


def _metric_target_status(
    value: float,
    direction: str,
    guardrail: float,
    target: float,
    stretch: float,
) -> str:
    if direction == "higher":
        if value >= stretch:
            return "stretch"
        if value >= target:
            return "target"
        if value >= guardrail:
            return "guardrail"
        return "below_guardrail"

    if value <= stretch:
        return "stretch"
    if value <= target:
        return "target"
    if value <= guardrail:
        return "guardrail"
    return "below_guardrail"


def _metric_value(metrics: dict[str, object], path: tuple[str, str]) -> float:
    section = metrics[path[0]]
    if not isinstance(section, dict):
        raise TypeError(f"Metric section {path[0]} is not a dictionary.")
    return float(section[path[1]])


def _build_metric_target_report(metrics: dict[str, object]) -> dict[str, dict[str, object]]:
    report = {}
    for metric_name, target_config in MODEL_METRIC_TARGETS.items():
        value = _metric_value(metrics, target_config["metric_path"])
        report[metric_name] = {
            "current": value,
            "direction": target_config["direction"],
            "guardrail": target_config["guardrail"],
            "target": target_config["target"],
            "stretch": target_config["stretch"],
            "status": _metric_target_status(
                value,
                str(target_config["direction"]),
                float(target_config["guardrail"]),
                float(target_config["target"]),
                float(target_config["stretch"]),
            ),
        }
    return report


def _fit_and_score_outcome_spec(
    spec: ModelSpec,
    fitting: pd.DataFrame,
    calibration: pd.DataFrame,
    holdout: pd.DataFrame,
    outcome_feature_medians: pd.Series,
) -> tuple[object, np.ndarray, float, dict[str, object]]:
    fitting_features = _prepare_training_features(
        fitting,
        OUTCOME_FEATURE_COLUMNS,
    ).fillna(outcome_feature_medians)
    calibration_features = _prepare_training_features(
        calibration,
        OUTCOME_FEATURE_COLUMNS,
    ).fillna(outcome_feature_medians)
    holdout_features = _prepare_training_features(
        holdout,
        OUTCOME_FEATURE_COLUMNS,
    ).fillna(outcome_feature_medians)

    outcome_model = spec.factory()
    outcome_model.fit(fitting_features, fitting["match_outcome"])
    classes = outcome_model.classes_
    fitting_probabilities = outcome_model.predict_proba(fitting_features)
    calibration_probabilities = outcome_model.predict_proba(calibration_features)
    holdout_probabilities = outcome_model.predict_proba(holdout_features)
    draw_probability_threshold = _best_draw_probability_threshold(
        calibration["match_outcome"],
        calibration_probabilities,
        classes,
    )

    metrics = {
        "model_type": spec.name,
        "draw_probability_threshold": draw_probability_threshold,
        "fitting": _score_outcome_predictions(
            fitting,
            fitting_probabilities,
            classes,
            draw_probability_threshold,
        ),
        "calibration": _score_outcome_predictions(
            calibration,
            calibration_probabilities,
            classes,
            draw_probability_threshold,
        ),
        "holdout": _score_outcome_predictions(
            holdout,
            holdout_probabilities,
            classes,
            draw_probability_threshold,
        ),
    }
    return outcome_model, classes, draw_probability_threshold, metrics


def train_goal_models(
    training_data: pd.DataFrame,
    historical_results: pd.DataFrame,
) -> tuple[TrainedGoalModels, dict[str, object]]:
    elo_features, current_elo_ratings = build_elo_features(historical_results)
    adjusted_form_features, current_adjusted_team_features = (
        build_opponent_adjusted_form_features(historical_results, elo_features)
    )
    model_data = training_data.merge(elo_features, on="result_id", how="inner")
    model_data = model_data.merge(adjusted_form_features, on="result_id", how="inner")
    model_data = model_data.dropna(subset=FEATURE_COLUMNS + ["home_score", "away_score"]).copy()
    model_data["match_date"] = pd.to_datetime(model_data["match_date"])
    model_data = model_data.sort_values(["match_date", "result_id"]).reset_index(drop=True)

    holdout_start = pd.Timestamp("2022-01-01")
    train = model_data[model_data["match_date"] < holdout_start]
    holdout = model_data[model_data["match_date"] >= holdout_start]
    calibration_mask = _tournament_calibration_mask(train, holdout_start)
    calibration = train[calibration_mask]
    fitting = train[~calibration_mask]

    if fitting.empty or calibration.empty or holdout.empty:
        raise ValueError("Fitting, calibration, and holdout sets must all contain rows.")

    candidate_results = []
    for spec in _model_specs():
        home_model, away_model, metrics = _fit_and_score_spec(
            spec,
            fitting,
            calibration,
            holdout,
        )
        candidate_results.append((spec, home_model, away_model, metrics))

    selected_goal_spec, selected_calibration_home_model, selected_calibration_away_model, selected_calibration_metrics = min(
        candidate_results,
        key=lambda item: item[3]["calibration"]["average_goals_mae"],
    )
    calibration_goal_features = _prepare_training_features(calibration, FEATURE_COLUMNS)
    selected_calibration_home_predictions = selected_calibration_home_model.predict(
        calibration_goal_features,
    )
    selected_calibration_away_predictions = selected_calibration_away_model.predict(
        calibration_goal_features,
    )

    outcome_candidate_results = []
    outcome_feature_medians = _prepare_training_features(
        fitting,
        OUTCOME_FEATURE_COLUMNS,
    ).median(numeric_only=True)
    calibration_outcome_features = _prepare_training_features(
        calibration,
        OUTCOME_FEATURE_COLUMNS,
    ).fillna(outcome_feature_medians)
    for spec in _outcome_model_specs():
        outcome_model, outcome_classes, draw_threshold, outcome_metrics = (
            _fit_and_score_outcome_spec(
                spec,
                fitting,
                calibration,
                holdout,
                outcome_feature_medians,
            )
        )
        calibration_outcome_probabilities = outcome_model.predict_proba(
            calibration_outcome_features,
        )
        scoreline_blend_weight, scoreline_blend_candidates = (
            _best_scoreline_outcome_blend_weight(
                calibration,
                selected_calibration_home_predictions,
                selected_calibration_away_predictions,
                calibration_outcome_probabilities,
                outcome_classes,
            )
        )
        scoreline_calibration_metrics = _score_reconciled_predictions(
            calibration,
            selected_calibration_home_predictions,
            selected_calibration_away_predictions,
            calibration_outcome_probabilities,
            outcome_classes,
            scoreline_blend_weight,
        )
        outcome_metrics["scoreline_outcome_blend_weight"] = scoreline_blend_weight
        outcome_metrics["scoreline_blend_candidates"] = scoreline_blend_candidates
        outcome_metrics["scoreline_calibration"] = scoreline_calibration_metrics
        outcome_candidate_results.append(
            (
                spec,
                outcome_model,
                outcome_classes,
                draw_threshold,
                outcome_metrics,
                scoreline_blend_weight,
                scoreline_blend_candidates,
                scoreline_calibration_metrics,
            )
        )

    (
        selected_outcome_spec,
        selected_calibration_outcome_model,
        selected_outcome_classes,
        selected_draw_threshold,
        selected_calibration_outcome_metrics,
        selected_scoreline_outcome_blend_weight,
        scoreline_blend_candidates,
        calibration_reconciled_metrics,
    ) = max(
        outcome_candidate_results,
        key=lambda item: (
            item[7]["match_outcome_accuracy"],
            item[7]["exact_score_accuracy"],
            item[4]["calibration"]["accuracy"],
        ),
    )

    selected_home_model, selected_away_model = _fit_goal_models(selected_goal_spec, train)
    train_features = _prepare_training_features(train, FEATURE_COLUMNS)
    outcome_feature_medians = _prepare_training_features(
        train,
        OUTCOME_FEATURE_COLUMNS,
    ).median(numeric_only=True)
    selected_train_outcome_features = _prepare_training_features(
        train,
        OUTCOME_FEATURE_COLUMNS,
    ).fillna(outcome_feature_medians)
    selected_outcome_model = selected_outcome_spec.factory()
    selected_outcome_model.fit(selected_train_outcome_features, train["match_outcome"])
    selected_outcome_classes = selected_outcome_model.classes_

    selected_train_goal_features = _prepare_training_features(train, FEATURE_COLUMNS)
    selected_holdout_goal_features = _prepare_training_features(holdout, FEATURE_COLUMNS)
    selected_holdout_outcome_features = _prepare_training_features(
        holdout,
        OUTCOME_FEATURE_COLUMNS,
    ).fillna(outcome_feature_medians)
    selected_train_home_predictions = selected_home_model.predict(selected_train_goal_features)
    selected_train_away_predictions = selected_away_model.predict(selected_train_goal_features)
    selected_train_outcome_probabilities = selected_outcome_model.predict_proba(
        selected_train_outcome_features,
    )
    selected_holdout_home_predictions = selected_home_model.predict(
        selected_holdout_goal_features,
    )
    selected_holdout_away_predictions = selected_away_model.predict(
        selected_holdout_goal_features,
    )
    selected_holdout_outcome_probabilities = selected_outcome_model.predict_proba(
        selected_holdout_outcome_features,
    )
    selected_metrics = {
        "model_type": selected_goal_spec.name,
        "training": _score_predictions(
            train,
            selected_train_home_predictions,
            selected_train_away_predictions,
        ),
        "holdout": _score_predictions(
            holdout,
            selected_holdout_home_predictions,
            selected_holdout_away_predictions,
        ),
    }
    selected_outcome_metrics = {
        "model_type": selected_outcome_spec.name,
        "draw_probability_threshold": selected_draw_threshold,
        "training": _score_outcome_predictions(
            train,
            selected_train_outcome_probabilities,
            selected_outcome_classes,
            selected_draw_threshold,
        ),
        "holdout": _score_outcome_predictions(
            holdout,
            selected_holdout_outcome_probabilities,
            selected_outcome_classes,
            selected_draw_threshold,
        ),
    }
    reconciled_training_metrics = _score_reconciled_predictions(
        train,
        selected_train_home_predictions,
        selected_train_away_predictions,
        selected_train_outcome_probabilities,
        selected_outcome_classes,
        selected_scoreline_outcome_blend_weight,
    )
    reconciled_holdout_metrics = _score_reconciled_predictions(
        holdout,
        selected_holdout_home_predictions,
        selected_holdout_away_predictions,
        selected_holdout_outcome_probabilities,
        selected_outcome_classes,
        selected_scoreline_outcome_blend_weight,
    )

    metrics = {
        "model_version": "v2",
        "selected_model_type": selected_metrics["model_type"],
        "selection_metric": "tournament_calibration.average_goals_mae",
        "selected_outcome_model_type": selected_outcome_metrics["model_type"],
        "outcome_selection_metric": "tournament_calibration.blended_scoreline_outcome_accuracy",
        "draw_probability_threshold": selected_draw_threshold,
        "scoreline_outcome_blend_weight": selected_scoreline_outcome_blend_weight,
        "scoreline_blend_selection_metric": (
            "tournament_calibration.match_outcome_accuracy with a minimum predicted draw-rate guardrail"
        ),
        "holdout_start": str(holdout_start.date()),
        "tournament_calibration": {
            "start": str(TOURNAMENT_CALIBRATION_START.date()),
            "end": str((holdout_start - pd.Timedelta(days=1)).date()),
            "rows": int(len(calibration)),
            "fitting_rows": int(len(fitting)),
            "tournaments": {
                str(key): int(value)
                for key, value in calibration["tournament"].value_counts().items()
            },
            "actual_distribution": {
                key: float(value)
                for key, value in calibration["match_outcome"]
                .value_counts(normalize=True)
                .items()
            },
            "selected_goal_model": selected_calibration_metrics,
            "selected_outcome_model": selected_calibration_outcome_metrics,
            "selected_scoreline_blend": calibration_reconciled_metrics,
        },
        "feature_columns": FEATURE_COLUMNS,
        "outcome_feature_columns": OUTCOME_FEATURE_COLUMNS,
        "candidate_models": [result[3] for result in candidate_results],
        "candidate_outcome_models": [result[4] for result in outcome_candidate_results],
        "scoreline_blend_candidates": scoreline_blend_candidates,
        "training": selected_metrics["training"],
        "holdout": selected_metrics["holdout"],
        "outcome_training": selected_outcome_metrics["training"],
        "outcome_holdout": selected_outcome_metrics["holdout"],
        "reconciled_training": reconciled_training_metrics,
        "reconciled_holdout": reconciled_holdout_metrics,
        "notes": [
            "V2 adds pre-match Elo features computed from historical international results and point-in-time FIFA ranking features.",
            "Raw last-10 form and goal difference are replaced in the model by Elo opponent-adjusted rolling form features.",
            "The script compares Poisson regression and histogram gradient boosting with Poisson loss.",
            "A direct outcome classifier chooses home/draw/away using dbt features plus external player aggregate match features.",
            "External match context flags are excluded from the outcome model because they behaved like fixture-order leakage for neutral tournament rows.",
            f"Draw threshold and scoreline blend selection use a 2018-2021 tournament-focused calibration slice with at least a {MIN_CALIBRATED_DRAW_RATE:.0%} predicted draw rate when such a setting is available.",
            "Final scorelines use a calibrated blend of independent Poisson score likelihood and direct outcome probabilities.",
            "dbt resolves known playoff placeholders and exposes model team names for joining to historical source names.",
            "Knockout predictions are resolved from the model-driven group standings and predicted sequentially through the bracket.",
            "Corners and card predictions use a dbt-built event profile from FootyStats international events and club player discipline stats.",
            "Rows with missing 2026 team-strength or Elo features use training-set median values as a fallback.",
        ],
    }
    metrics["metric_targets"] = _build_metric_target_report(metrics)

    return (
        TrainedGoalModels(
            home_model=selected_home_model,
            away_model=selected_away_model,
            outcome_model=selected_outcome_model,
            feature_medians=train_features.median(numeric_only=True),
            outcome_feature_medians=outcome_feature_medians,
            current_elo_ratings=current_elo_ratings,
            current_adjusted_team_features=current_adjusted_team_features,
            selected_model_name=selected_metrics["model_type"],
            selected_outcome_model_name=selected_outcome_metrics["model_type"],
            outcome_classes=selected_outcome_classes,
            draw_probability_threshold=selected_draw_threshold,
            scoreline_outcome_blend_weight=selected_scoreline_outcome_blend_weight,
        ),
        metrics,
    )


def _is_neutral_world_cup_match(home_team: object, away_team: object) -> int:
    canonical_home = canonical_team_name(home_team)
    canonical_away = canonical_team_name(away_team)
    return int(canonical_home not in HOST_TEAMS and canonical_away not in HOST_TEAMS)


def _team_strength_lookup(team_strength: pd.DataFrame) -> dict[str, pd.Series]:
    lookup: dict[str, pd.Series] = {}
    for row in team_strength.itertuples(index=False):
        row_data = pd.Series(row._asdict())
        lookup[_normalise_text(row_data["team_name"])] = row_data
    return lookup


def _team_metric(
    team_name: object,
    metric_name: str,
    team_strength_lookup: dict[str, pd.Series],
) -> float:
    canonical_name = canonical_team_name(team_name)
    team_row = team_strength_lookup.get(_normalise_text(canonical_name))
    if team_row is None:
        return np.nan
    return float(team_row[metric_name])


def _squad_metric(
    team_name: object,
    metric_name: str,
    squad_strength_lookup: dict[str, pd.Series],
) -> float:
    canonical_name = canonical_team_name(team_name)
    squad_row = squad_strength_lookup.get(_normalise_text(canonical_name))
    if squad_row is None:
        return 0.0

    value = squad_row.get(metric_name, np.nan)
    if pd.isna(value):
        return 0.0
    return float(value)


def _event_defaults(team_event_profile: pd.DataFrame) -> dict[str, float]:
    defaults = {
        "avg_corners_for": DEFAULT_TOTAL_CORNERS / 2,
        "avg_corners_against": DEFAULT_TOTAL_CORNERS / 2,
        "blended_yellow_cards_for": DEFAULT_TOTAL_YELLOW_CARDS / 2,
        "avg_yellow_cards_against": DEFAULT_TOTAL_YELLOW_CARDS / 2,
        "blended_red_cards_for": DEFAULT_TOTAL_RED_CARDS / 2,
        "avg_red_cards_against": DEFAULT_TOTAL_RED_CARDS / 2,
    }
    for metric_name in defaults:
        if metric_name in team_event_profile.columns:
            metric_values = pd.to_numeric(team_event_profile[metric_name], errors="coerce")
            if metric_values.notna().any():
                defaults[metric_name] = float(metric_values.mean())
    return defaults


def _event_metric(
    team_name: object,
    metric_name: str,
    team_event_lookup: dict[str, pd.Series],
    defaults: dict[str, float],
) -> float:
    canonical_name = canonical_team_name(team_name)
    event_row = team_event_lookup.get(_normalise_text(canonical_name))
    if event_row is None:
        return defaults[metric_name]

    value = event_row.get(metric_name, np.nan)
    if pd.isna(value):
        return defaults[metric_name]
    return float(value)


def _fifa_ranking_defaults(latest_fifa_rankings: pd.DataFrame) -> dict[str, float]:
    return {
        "fifa_rank": float(pd.to_numeric(latest_fifa_rankings["fifa_rank"]).median()),
        "fifa_points": float(pd.to_numeric(latest_fifa_rankings["fifa_points"]).median()),
    }


def _fifa_metric(
    team_name: object,
    metric_name: str,
    fifa_ranking_lookup: dict[str, pd.Series],
    defaults: dict[str, float],
) -> float:
    canonical_name = canonical_team_name(team_name)
    ranking_row = fifa_ranking_lookup.get(_normalise_text(canonical_name))
    if ranking_row is None:
        return defaults[metric_name]

    value = ranking_row.get(metric_name, np.nan)
    if pd.isna(value):
        return defaults[metric_name]
    return float(value)


def _external_player_strength_defaults(external_player_strength: pd.DataFrame) -> dict[str, float]:
    metric_names = [
        "avg_overall",
        "max_overall",
        "avg_attack_overall",
        "avg_defense_overall",
        "avg_pace",
        "avg_shooting",
        "avg_passing",
    ]
    defaults = {}
    for metric_name in metric_names:
        metric_values = pd.to_numeric(external_player_strength[metric_name], errors="coerce")
        defaults[metric_name] = float(metric_values.median())
    return defaults


def _external_player_metric(
    team_name: object,
    metric_name: str,
    external_player_lookup: dict[str, pd.Series],
    defaults: dict[str, float],
) -> float:
    canonical_name = canonical_team_name(team_name)
    player_row = external_player_lookup.get(_normalise_text(canonical_name))
    if player_row is None:
        return defaults[metric_name]

    value = player_row.get(metric_name, np.nan)
    if pd.isna(value):
        return defaults[metric_name]
    return float(value)


def _elo_rating(team_name: object, models: TrainedGoalModels) -> float:
    return float(models.current_elo_ratings.get(canonical_team_name(team_name), DEFAULT_ELO))


def _adjusted_team_metric(
    team_name: object,
    metric_name: str,
    models: TrainedGoalModels,
) -> float:
    canonical_name = canonical_team_name(team_name)
    team_features = models.current_adjusted_team_features.get(_normalise_text(canonical_name))
    if team_features is None:
        return np.nan
    return float(team_features.get(metric_name, np.nan))


def _team_tiebreak_strength(
    team_name: object,
    latest_fifa_rankings: pd.DataFrame,
    external_player_strength: pd.DataFrame,
    models: TrainedGoalModels,
) -> float:
    fifa_lookup = _team_strength_lookup(latest_fifa_rankings)
    fifa_defaults = _fifa_ranking_defaults(latest_fifa_rankings)
    player_lookup = _team_strength_lookup(external_player_strength)
    player_defaults = _external_player_strength_defaults(external_player_strength)

    elo_score = _elo_rating(team_name, models)
    fifa_points = _fifa_metric(team_name, "fifa_points", fifa_lookup, fifa_defaults)
    player_overall = _external_player_metric(
        team_name,
        "avg_overall",
        player_lookup,
        player_defaults,
    )
    return elo_score + (0.6 * fifa_points) + (20.0 * player_overall)


def _group_tiebreak_strengths(
    group_predictions: pd.DataFrame,
    latest_fifa_rankings: pd.DataFrame,
    external_player_strength: pd.DataFrame,
    models: TrainedGoalModels,
) -> dict[str, float]:
    teams = sorted(
        {canonical_team_name(team) for team in group_predictions["home_team"].tolist()}
        | {canonical_team_name(team) for team in group_predictions["away_team"].tolist()}
    )
    return {
        team: _team_tiebreak_strength(
            team,
            latest_fifa_rankings,
            external_player_strength,
            models,
        )
        for team in teams
    }


def _row_team_name_for_model(row: object, side: str) -> str:
    model_attribute = f"{side}_team_model_name"
    if hasattr(row, model_attribute):
        model_name = getattr(row, model_attribute)
        if pd.notna(model_name):
            return str(model_name)
    return canonical_team_name(getattr(row, f"{side}_team"))


def _prepare_world_cup_match_features(
    matches: pd.DataFrame,
    team_strength: pd.DataFrame,
    latest_fifa_rankings: pd.DataFrame,
    models: TrainedGoalModels,
    external_player_strength: pd.DataFrame | None = None,
    feature_columns: list[str] | None = None,
) -> pd.DataFrame:
    if feature_columns is None:
        feature_columns = FEATURE_COLUMNS

    strength_lookup = _team_strength_lookup(team_strength)
    fifa_ranking_lookup = _team_strength_lookup(latest_fifa_rankings)
    fifa_defaults = _fifa_ranking_defaults(latest_fifa_rankings)
    external_player_lookup = (
        _team_strength_lookup(external_player_strength)
        if external_player_strength is not None
        else {}
    )
    external_player_defaults = (
        _external_player_strength_defaults(external_player_strength)
        if external_player_strength is not None
        else {}
    )
    rows = []

    for row in matches.itertuples(index=False):
        home_team = _row_team_name_for_model(row, "home")
        away_team = _row_team_name_for_model(row, "away")
        home_elo = _elo_rating(home_team, models)
        away_elo = _elo_rating(away_team, models)
        neutral = _is_neutral_world_cup_match(home_team, away_team)

        home_adjusted_points = _adjusted_team_metric(
            home_team,
            "last_10_adjusted_points_per_match",
            models,
        )
        away_adjusted_points = _adjusted_team_metric(
            away_team,
            "last_10_adjusted_points_per_match",
            models,
        )
        home_adjusted_goal_diff = _adjusted_team_metric(
            home_team,
            "last_10_adjusted_goal_diff_per_match",
            models,
        )
        away_adjusted_goal_diff = _adjusted_team_metric(
            away_team,
            "last_10_adjusted_goal_diff_per_match",
            models,
        )
        home_goals_for = _team_metric(home_team, "last_10_goals_for_per_match", strength_lookup)
        away_goals_for = _team_metric(away_team, "last_10_goals_for_per_match", strength_lookup)
        home_goals_against = _team_metric(
            home_team,
            "last_10_goals_against_per_match",
            strength_lookup,
        )
        away_goals_against = _team_metric(
            away_team,
            "last_10_goals_against_per_match",
            strength_lookup,
        )
        home_fifa_rank = _fifa_metric(
            home_team,
            "fifa_rank",
            fifa_ranking_lookup,
            fifa_defaults,
        )
        away_fifa_rank = _fifa_metric(
            away_team,
            "fifa_rank",
            fifa_ranking_lookup,
            fifa_defaults,
        )
        home_fifa_points = _fifa_metric(
            home_team,
            "fifa_points",
            fifa_ranking_lookup,
            fifa_defaults,
        )
        away_fifa_points = _fifa_metric(
            away_team,
            "fifa_points",
            fifa_ranking_lookup,
            fifa_defaults,
        )
        home_external_overall = _external_player_metric(
            home_team,
            "avg_overall",
            external_player_lookup,
            external_player_defaults,
        ) if external_player_strength is not None else np.nan
        away_external_overall = _external_player_metric(
            away_team,
            "avg_overall",
            external_player_lookup,
            external_player_defaults,
        ) if external_player_strength is not None else np.nan
        home_external_attack = _external_player_metric(
            home_team,
            "avg_attack_overall",
            external_player_lookup,
            external_player_defaults,
        ) if external_player_strength is not None else np.nan
        away_external_attack = _external_player_metric(
            away_team,
            "avg_attack_overall",
            external_player_lookup,
            external_player_defaults,
        ) if external_player_strength is not None else np.nan
        home_external_defense = _external_player_metric(
            home_team,
            "avg_defense_overall",
            external_player_lookup,
            external_player_defaults,
        ) if external_player_strength is not None else np.nan
        away_external_defense = _external_player_metric(
            away_team,
            "avg_defense_overall",
            external_player_lookup,
            external_player_defaults,
        ) if external_player_strength is not None else np.nan
        home_last_10_matches = _team_metric(home_team, "last_10_matches", strength_lookup)
        away_last_10_matches = _team_metric(away_team, "last_10_matches", strength_lookup)
        home_last_10_wins = _team_metric(home_team, "last_10_wins", strength_lookup)
        away_last_10_wins = _team_metric(away_team, "last_10_wins", strength_lookup)

        rows.append(
            {
                "neutral": neutral,
                "home_prior_10_adjusted_points_per_match": home_adjusted_points,
                "away_prior_10_adjusted_points_per_match": away_adjusted_points,
                "home_prior_10_adjusted_goal_diff_per_match": home_adjusted_goal_diff,
                "away_prior_10_adjusted_goal_diff_per_match": away_adjusted_goal_diff,
                "home_prior_10_goals_for_per_match": home_goals_for,
                "away_prior_10_goals_for_per_match": away_goals_for,
                "home_prior_10_goals_against_per_match": home_goals_against,
                "away_prior_10_goals_against_per_match": away_goals_against,
                "prior_10_adjusted_points_per_match_diff": (
                    home_adjusted_points - away_adjusted_points
                ),
                "prior_10_adjusted_goal_diff_per_match_diff": (
                    home_adjusted_goal_diff - away_adjusted_goal_diff
                ),
                "prior_10_goals_for_per_match_diff": home_goals_for - away_goals_for,
                "prior_10_goals_against_per_match_diff": home_goals_against
                - away_goals_against,
                "home_fifa_rank": home_fifa_rank,
                "away_fifa_rank": away_fifa_rank,
                "home_fifa_points": home_fifa_points,
                "away_fifa_points": away_fifa_points,
                "fifa_rank_diff": home_fifa_rank - away_fifa_rank,
                "fifa_points_diff": home_fifa_points - away_fifa_points,
                "home_pre_match_elo": home_elo,
                "away_pre_match_elo": away_elo,
                "pre_match_elo_diff": home_elo - away_elo,
                "home_elo_expected_result": _elo_expected_score(
                    home_elo,
                    away_elo,
                    bool(neutral),
                ),
                "external_home_elo": home_elo,
                "external_away_elo": away_elo,
                "external_elo_diff": home_elo - away_elo,
                "external_home_avg_overall": home_external_overall,
                "external_home_max_overall": _external_player_metric(
                    home_team,
                    "max_overall",
                    external_player_lookup,
                    external_player_defaults,
                ) if external_player_strength is not None else np.nan,
                "external_home_avg_attack": home_external_attack,
                "external_home_avg_defense": home_external_defense,
                "external_home_avg_pace": _external_player_metric(
                    home_team,
                    "avg_pace",
                    external_player_lookup,
                    external_player_defaults,
                ) if external_player_strength is not None else np.nan,
                "external_home_avg_shooting": _external_player_metric(
                    home_team,
                    "avg_shooting",
                    external_player_lookup,
                    external_player_defaults,
                ) if external_player_strength is not None else np.nan,
                "external_home_avg_passing": _external_player_metric(
                    home_team,
                    "avg_passing",
                    external_player_lookup,
                    external_player_defaults,
                ) if external_player_strength is not None else np.nan,
                "external_away_avg_overall": away_external_overall,
                "external_away_max_overall": _external_player_metric(
                    away_team,
                    "max_overall",
                    external_player_lookup,
                    external_player_defaults,
                ) if external_player_strength is not None else np.nan,
                "external_away_avg_attack": away_external_attack,
                "external_away_avg_defense": away_external_defense,
                "external_away_avg_pace": _external_player_metric(
                    away_team,
                    "avg_pace",
                    external_player_lookup,
                    external_player_defaults,
                ) if external_player_strength is not None else np.nan,
                "external_away_avg_shooting": _external_player_metric(
                    away_team,
                    "avg_shooting",
                    external_player_lookup,
                    external_player_defaults,
                ) if external_player_strength is not None else np.nan,
                "external_away_avg_passing": _external_player_metric(
                    away_team,
                    "avg_passing",
                    external_player_lookup,
                    external_player_defaults,
                ) if external_player_strength is not None else np.nan,
                "external_overall_diff": home_external_overall - away_external_overall,
                "external_attack_diff": home_external_attack - away_external_attack,
                "external_defense_diff": home_external_defense - away_external_defense,
                "external_home_form_scored": home_goals_for,
                "external_home_form_conceded": home_goals_against,
                "external_home_form_win_rate": home_last_10_wins / max(home_last_10_matches, 1),
                "external_away_form_scored": away_goals_for,
                "external_away_form_conceded": away_goals_against,
                "external_away_form_win_rate": away_last_10_wins / max(away_last_10_matches, 1),
                "external_is_neutral": neutral,
                "external_is_world_cup": 1,
                "external_is_continental": 0,
                "has_external_match_features": int(external_player_strength is not None),
            }
        )

    features = pd.DataFrame(rows)
    features = features[feature_columns]
    medians = (
        models.outcome_feature_medians
        if feature_columns == OUTCOME_FEATURE_COLUMNS
        else models.feature_medians
    )
    return features.fillna(medians)


def predict_world_cup_group_matches(
    world_cup_matches: pd.DataFrame,
    team_strength: pd.DataFrame,
    squad_strength: pd.DataFrame,
    latest_fifa_rankings: pd.DataFrame,
    external_player_strength: pd.DataFrame,
    team_event_profile: pd.DataFrame,
    models: TrainedGoalModels,
) -> pd.DataFrame:
    home_expected_goals, away_expected_goals = _predict_expected_goals(
        world_cup_matches,
        team_strength,
        squad_strength,
        latest_fifa_rankings,
        models,
    )
    outcome_predictions = _predict_match_outcomes(
        world_cup_matches,
        team_strength,
        latest_fifa_rankings,
        external_player_strength,
        models,
    )
    outcome_probability_columns = [
        f"outcome_probability_{class_name}" for class_name in models.outcome_classes
    ]
    reconciled_scores = [
        _select_blended_scoreline(
            float(home_goals),
            float(away_goals),
            probabilities,
            models.outcome_classes,
            models.scoreline_outcome_blend_weight,
        )
        for home_goals, away_goals, probabilities in zip(
            home_expected_goals,
            away_expected_goals,
            outcome_predictions[outcome_probability_columns].to_numpy(),
        )
    ]
    predicted_home_goals = np.array([score[0] for score in reconciled_scores])
    predicted_away_goals = np.array([score[1] for score in reconciled_scores])

    predictions = world_cup_matches[
        ["match_id", "group_letter", "home_team", "away_team", "match_date_utc", "venue"]
    ].copy()
    predictions = predictions.rename(columns={"group_letter": "group", "match_date_utc": "date_utc"})
    predictions["date_utc"] = pd.to_datetime(predictions["date_utc"]).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    predictions["predicted_home_goals"] = predicted_home_goals
    predictions["predicted_away_goals"] = predicted_away_goals
    event_predictions = _predict_event_counts(world_cup_matches, team_event_profile)
    predictions["corners"] = event_predictions["corners"].to_numpy()
    predictions["yellow_cards"] = event_predictions["yellow_cards"].to_numpy()
    predictions["red_cards"] = event_predictions["red_cards"].to_numpy()
    predictions["winning_team"] = [
        outcome_from_scores(int(home_goals), int(away_goals))
        for home_goals, away_goals in zip(predicted_home_goals, predicted_away_goals)
    ]

    predictions["_match_id_sort"] = pd.to_numeric(predictions["match_id"])
    predictions = predictions.sort_values("_match_id_sort").drop(columns="_match_id_sort")

    return predictions[
        [
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
    ]


def _normalise_knockout_slots(knockout_slots: pd.DataFrame) -> pd.DataFrame:
    slots = knockout_slots.rename(
        columns={
            "round_name": "round",
            "score_multiplier": "multiplier",
            "match_date_utc": "date_utc",
        }
    ).copy()
    slots["date_utc"] = pd.to_datetime(slots["date_utc"]).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return slots[
        ["match_id", "round", "multiplier", "date_utc", "venue", "slot_home", "slot_away"]
    ]


def _predict_expected_goals(
    matches: pd.DataFrame,
    team_strength: pd.DataFrame,
    squad_strength: pd.DataFrame,
    latest_fifa_rankings: pd.DataFrame,
    models: TrainedGoalModels,
) -> tuple[np.ndarray, np.ndarray]:
    features = _prepare_world_cup_match_features(
        matches,
        team_strength,
        latest_fifa_rankings,
        models,
    )
    home_expected_goals = models.home_model.predict(features)
    away_expected_goals = models.away_model.predict(features)
    return _apply_squad_goal_overlay(
        matches,
        home_expected_goals,
        away_expected_goals,
        squad_strength,
    )


def _predict_match_outcomes(
    matches: pd.DataFrame,
    team_strength: pd.DataFrame,
    latest_fifa_rankings: pd.DataFrame,
    external_player_strength: pd.DataFrame,
    models: TrainedGoalModels,
) -> pd.DataFrame:
    features = _prepare_world_cup_match_features(
        matches,
        team_strength,
        latest_fifa_rankings,
        models,
        external_player_strength,
        OUTCOME_FEATURE_COLUMNS,
    )
    probabilities = models.outcome_model.predict_proba(features)
    predictions = _outcomes_from_probabilities(
        probabilities,
        models.outcome_classes,
        models.draw_probability_threshold,
    )
    probability_frame = pd.DataFrame(
        probabilities,
        columns=[f"outcome_probability_{class_name}" for class_name in models.outcome_classes],
    )
    probability_frame["predicted_outcome"] = predictions
    return probability_frame


def _predict_event_counts(
    matches: pd.DataFrame,
    team_event_profile: pd.DataFrame,
    round_names: list[str | None] | None = None,
) -> pd.DataFrame:
    event_lookup = _team_strength_lookup(team_event_profile)
    defaults = _event_defaults(team_event_profile)
    if round_names is None:
        round_names = [None] * len(matches)

    rows = []
    for row, round_name in zip(matches.itertuples(index=False), round_names):
        home_team = _row_team_name_for_model(row, "home")
        away_team = _row_team_name_for_model(row, "away")

        expected_corners = (
            _event_metric(home_team, "avg_corners_for", event_lookup, defaults)
            + _event_metric(away_team, "avg_corners_for", event_lookup, defaults)
            + _event_metric(home_team, "avg_corners_against", event_lookup, defaults)
            + _event_metric(away_team, "avg_corners_against", event_lookup, defaults)
        ) / 2
        expected_yellow_cards = (
            _event_metric(home_team, "blended_yellow_cards_for", event_lookup, defaults)
            + _event_metric(away_team, "blended_yellow_cards_for", event_lookup, defaults)
            + _event_metric(home_team, "avg_yellow_cards_against", event_lookup, defaults)
            + _event_metric(away_team, "avg_yellow_cards_against", event_lookup, defaults)
        ) / 2
        expected_red_cards = (
            _event_metric(home_team, "blended_red_cards_for", event_lookup, defaults)
            + _event_metric(away_team, "blended_red_cards_for", event_lookup, defaults)
            + _event_metric(home_team, "avg_red_cards_against", event_lookup, defaults)
            + _event_metric(away_team, "avg_red_cards_against", event_lookup, defaults)
        ) / 2

        yellow_adjustment = KNOCKOUT_YELLOW_CARD_ADJUSTMENTS.get(str(round_name), 0.0)
        expected_yellow_cards += yellow_adjustment
        expected_red_cards += yellow_adjustment * KNOCKOUT_RED_CARD_ADJUSTMENT_FACTOR

        rows.append(
            {
                "corners": int(np.clip(np.rint(expected_corners), 4, 17)),
                "yellow_cards": int(np.clip(np.rint(expected_yellow_cards), 1, 9)),
                "red_cards": int(np.clip(expected_red_cards >= 0.55, 0, 2)),
                "expected_corners": float(expected_corners),
                "expected_yellow_cards": float(expected_yellow_cards),
                "expected_red_cards": float(expected_red_cards),
            }
        )

    return pd.DataFrame(rows)


def _apply_squad_goal_overlay(
    matches: pd.DataFrame,
    home_expected_goals: np.ndarray,
    away_expected_goals: np.ndarray,
    squad_strength: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray]:
    squad_lookup = _team_strength_lookup(squad_strength)
    adjusted_home_goals = []
    adjusted_away_goals = []

    for row, base_home_goals, base_away_goals in zip(
        matches.itertuples(index=False),
        home_expected_goals,
        away_expected_goals,
    ):
        home_team = _row_team_name_for_model(row, "home")
        away_team = _row_team_name_for_model(row, "away")

        home_overall = _squad_metric(home_team, "overall_star_power_z", squad_lookup)
        away_overall = _squad_metric(away_team, "overall_star_power_z", squad_lookup)
        home_attack = _squad_metric(home_team, "attacking_star_power_z", squad_lookup)
        away_attack = _squad_metric(away_team, "attacking_star_power_z", squad_lookup)
        home_defense = _squad_metric(home_team, "defensive_experience_z", squad_lookup)
        away_defense = _squad_metric(away_team, "defensive_experience_z", squad_lookup)
        home_experience = _squad_metric(home_team, "experience_score_z", squad_lookup)
        away_experience = _squad_metric(away_team, "experience_score_z", squad_lookup)

        home_adjustment = np.clip(
            SQUAD_OVERALL_WEIGHT * (home_overall - away_overall)
            + SQUAD_ATTACK_DEFENSE_WEIGHT * (home_attack - away_defense)
            + SQUAD_EXPERIENCE_WEIGHT * (home_experience - away_experience),
            -SQUAD_GOAL_ADJUSTMENT_CAP,
            SQUAD_GOAL_ADJUSTMENT_CAP,
        )
        away_adjustment = np.clip(
            SQUAD_OVERALL_WEIGHT * (away_overall - home_overall)
            + SQUAD_ATTACK_DEFENSE_WEIGHT * (away_attack - home_defense)
            + SQUAD_EXPERIENCE_WEIGHT * (away_experience - home_experience),
            -SQUAD_GOAL_ADJUSTMENT_CAP,
            SQUAD_GOAL_ADJUSTMENT_CAP,
        )

        adjusted_home_goals.append(max(0.05, float(base_home_goals) + float(home_adjustment)))
        adjusted_away_goals.append(max(0.05, float(base_away_goals) + float(away_adjustment)))

    return np.array(adjusted_home_goals), np.array(adjusted_away_goals)


def _knockout_match_winner(
    home_team: str,
    away_team: str,
    home_goals: int,
    away_goals: int,
    home_expected_goals: float,
    away_expected_goals: float,
    models: TrainedGoalModels,
) -> tuple[str, bool]:
    if home_goals > away_goals:
        return "home", False
    if away_goals > home_goals:
        return "away", False

    if home_expected_goals > away_expected_goals:
        return "home", True
    if away_expected_goals > home_expected_goals:
        return "away", True
    return (
        "home" if _elo_rating(home_team, models) >= _elo_rating(away_team, models) else "away",
        True,
    )


def predict_world_cup_knockout_matches(
    knockout_slots: pd.DataFrame,
    group_predictions: pd.DataFrame,
    team_strength: pd.DataFrame,
    squad_strength: pd.DataFrame,
    latest_fifa_rankings: pd.DataFrame,
    external_player_strength: pd.DataFrame,
    team_event_profile: pd.DataFrame,
    models: TrainedGoalModels,
) -> pd.DataFrame:
    slots = _normalise_knockout_slots(knockout_slots)
    standings = build_group_standings(
        group_predictions,
        _group_tiebreak_strengths(
            group_predictions,
            latest_fifa_rankings,
            external_player_strength,
            models,
        ),
    )
    match_results: dict[int, dict[str, str]] = {}
    used_third_groups: set[str] = set()
    predictions = []

    sorted_slots = slots.assign(_match_id_sort=pd.to_numeric(slots["match_id"])).sort_values(
        "_match_id_sort"
    )
    for row in sorted_slots.drop(columns="_match_id_sort").itertuples(index=False):
        row_data = row._asdict()
        match_id = int(row_data["match_id"])
        predicted_home_team = resolve_knockout_slot(
            str(row_data["slot_home"]),
            standings,
            match_results,
            used_third_groups,
        )
        predicted_away_team = resolve_knockout_slot(
            str(row_data["slot_away"]),
            standings,
            match_results,
            used_third_groups,
        )

        match = pd.DataFrame(
            [
                {
                    "home_team": predicted_home_team,
                    "away_team": predicted_away_team,
                }
            ]
        )
        home_expected_goals, away_expected_goals = _predict_expected_goals(
            match,
            team_strength,
            squad_strength,
            latest_fifa_rankings,
            models,
        )
        outcome_predictions = _predict_match_outcomes(
            match,
            team_strength,
            latest_fifa_rankings,
            external_player_strength,
            models,
        )
        outcome_probability_columns = [
            f"outcome_probability_{class_name}" for class_name in models.outcome_classes
        ]
        home_goals, away_goals = _select_blended_scoreline(
            float(home_expected_goals[0]),
            float(away_expected_goals[0]),
            outcome_predictions.loc[0, outcome_probability_columns].to_numpy(),
            models.outcome_classes,
            models.scoreline_outcome_blend_weight,
        )
        predicted_outcome = outcome_from_scores(home_goals, away_goals)
        if predicted_outcome == "draw":
            home_strength = _team_tiebreak_strength(
                predicted_home_team,
                latest_fifa_rankings,
                external_player_strength,
                models,
            )
            away_strength = _team_tiebreak_strength(
                predicted_away_team,
                latest_fifa_rankings,
                external_player_strength,
                models,
            )
            match_winner = "home" if home_strength >= away_strength else "away"
            penalties = True
        else:
            match_winner = predicted_outcome
            penalties = False
        event_counts = _predict_event_counts(
            match,
            team_event_profile,
            round_names=[str(row_data["round"])],
        ).iloc[0]
        winner_team = predicted_home_team if match_winner == "home" else predicted_away_team
        loser_team = predicted_away_team if match_winner == "home" else predicted_home_team
        match_results[match_id] = {"winner_team": winner_team, "loser_team": loser_team}

        predictions.append(
            {
                **row_data,
                "predicted_home_team": predicted_home_team,
                "predicted_away_team": predicted_away_team,
                "predicted_home_goals": home_goals,
                "predicted_away_goals": away_goals,
                "corners": int(event_counts["corners"]),
                "yellow_cards": int(event_counts["yellow_cards"]),
                "red_cards": int(event_counts["red_cards"]),
                "match_winner": match_winner,
                "penalties": penalties,
            }
        )

    return pd.DataFrame(predictions)[
        [
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
    ]


def build_model_predictions(
    group_predictions: pd.DataFrame,
    knockout_predictions: pd.DataFrame,
) -> pd.DataFrame:
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
    combined = pd.concat(
        [group_combined[combined_columns], knockout_combined[combined_columns]],
        ignore_index=True,
    )
    combined["_match_id_sort"] = pd.to_numeric(combined["match_id"])
    return combined.sort_values("_match_id_sort").drop(columns="_match_id_sort")


def build_model_team_features(
    team_strength: pd.DataFrame,
    models: TrainedGoalModels,
) -> pd.DataFrame:
    rows = []
    for row in team_strength.sort_values("team_name").itertuples(index=False):
        team_name = canonical_team_name(row.team_name)
        rows.append(
            {
                "team_model_name": team_name,
                "current_elo": round(_elo_rating(team_name, models), 1),
                "last_10_adjusted_points_per_match": round(
                    _adjusted_team_metric(
                        team_name,
                        "last_10_adjusted_points_per_match",
                        models,
                    ),
                    3,
                ),
                "last_10_adjusted_goal_diff_per_match": round(
                    _adjusted_team_metric(
                        team_name,
                        "last_10_adjusted_goal_diff_per_match",
                        models,
                    ),
                    3,
                ),
            }
        )
    return pd.DataFrame(rows)


def _sample_scoreline(distribution: pd.DataFrame, rng: np.random.Generator) -> tuple[int, int]:
    selected_index = int(rng.choice(len(distribution), p=distribution["probability"].to_numpy()))
    row = distribution.iloc[selected_index]
    return int(row["home_goals"]), int(row["away_goals"])


def _penalty_home_win_probability(
    home_team: str,
    away_team: str,
    models: TrainedGoalModels,
) -> float:
    return _elo_expected_score(
        _elo_rating(home_team, models),
        _elo_rating(away_team, models),
        neutral=True,
    )


def _group_scoreline_distributions(
    world_cup_matches: pd.DataFrame,
    team_strength: pd.DataFrame,
    squad_strength: pd.DataFrame,
    latest_fifa_rankings: pd.DataFrame,
    external_player_strength: pd.DataFrame,
    models: TrainedGoalModels,
) -> list[pd.DataFrame]:
    home_expected_goals, away_expected_goals = _predict_expected_goals(
        world_cup_matches,
        team_strength,
        squad_strength,
        latest_fifa_rankings,
        models,
    )
    outcome_predictions = _predict_match_outcomes(
        world_cup_matches,
        team_strength,
        latest_fifa_rankings,
        external_player_strength,
        models,
    )
    outcome_probability_columns = [
        f"outcome_probability_{class_name}" for class_name in models.outcome_classes
    ]
    return [
        _scoreline_probability_grid(
            float(home_goals),
            float(away_goals),
            probabilities,
            models.outcome_classes,
            models.scoreline_outcome_blend_weight,
        )
        for home_goals, away_goals, probabilities in zip(
            home_expected_goals,
            away_expected_goals,
            outcome_predictions[outcome_probability_columns].to_numpy(),
        )
    ]


def _match_distribution_for_teams(
    home_team: str,
    away_team: str,
    team_strength: pd.DataFrame,
    squad_strength: pd.DataFrame,
    latest_fifa_rankings: pd.DataFrame,
    external_player_strength: pd.DataFrame,
    models: TrainedGoalModels,
    distribution_cache: dict[tuple[str, str], tuple[pd.DataFrame, float]],
) -> tuple[pd.DataFrame, float]:
    cache_key = (_normalise_text(home_team), _normalise_text(away_team))
    if cache_key in distribution_cache:
        return distribution_cache[cache_key]

    match = pd.DataFrame([{"home_team": home_team, "away_team": away_team}])
    home_expected_goals, away_expected_goals = _predict_expected_goals(
        match,
        team_strength,
        squad_strength,
        latest_fifa_rankings,
        models,
    )
    outcome_predictions = _predict_match_outcomes(
        match,
        team_strength,
        latest_fifa_rankings,
        external_player_strength,
        models,
    )
    outcome_probability_columns = [
        f"outcome_probability_{class_name}" for class_name in models.outcome_classes
    ]
    distribution = _scoreline_probability_grid(
        float(home_expected_goals[0]),
        float(away_expected_goals[0]),
        outcome_predictions.loc[0, outcome_probability_columns].to_numpy(),
        models.outcome_classes,
        models.scoreline_outcome_blend_weight,
    )
    penalty_home_probability = _penalty_home_win_probability(home_team, away_team, models)
    distribution_cache[cache_key] = (distribution, penalty_home_probability)
    return distribution, penalty_home_probability


def _sample_knockout_result(
    home_team: str,
    away_team: str,
    team_strength: pd.DataFrame,
    squad_strength: pd.DataFrame,
    latest_fifa_rankings: pd.DataFrame,
    external_player_strength: pd.DataFrame,
    models: TrainedGoalModels,
    distribution_cache: dict[tuple[str, str], tuple[pd.DataFrame, float]],
    rng: np.random.Generator,
) -> dict[str, object]:
    distribution, penalty_home_probability = _match_distribution_for_teams(
        home_team,
        away_team,
        team_strength,
        squad_strength,
        latest_fifa_rankings,
        external_player_strength,
        models,
        distribution_cache,
    )
    home_goals, away_goals = _sample_scoreline(distribution, rng)
    if home_goals > away_goals:
        winner_label = "home"
        penalties = False
    elif away_goals > home_goals:
        winner_label = "away"
        penalties = False
    else:
        winner_label = "home" if rng.random() < penalty_home_probability else "away"
        penalties = True

    winner_team = home_team if winner_label == "home" else away_team
    loser_team = away_team if winner_label == "home" else home_team
    return {
        "home_goals": home_goals,
        "away_goals": away_goals,
        "winner_label": winner_label,
        "winner_team": winner_team,
        "loser_team": loser_team,
        "penalties": penalties,
    }


def _increment_reached_round(
    round_counts: dict[str, dict[str, int]],
    team_name: str,
    round_name: str,
) -> None:
    round_key_by_name = {
        "Round of 32": "round_of_32_count",
        "Round of 16": "round_of_16_count",
        "Quarter-final": "quarter_final_count",
        "Semi-final": "semi_final_count",
        "Final": "final_count",
    }
    round_key = round_key_by_name.get(round_name)
    if round_key is not None:
        round_counts[team_name][round_key] += 1


def simulate_tournament_probabilities(
    world_cup_matches: pd.DataFrame,
    knockout_slots: pd.DataFrame,
    team_strength: pd.DataFrame,
    squad_strength: pd.DataFrame,
    latest_fifa_rankings: pd.DataFrame,
    external_player_strength: pd.DataFrame,
    models: TrainedGoalModels,
    simulation_runs: int = TOURNAMENT_SIMULATION_RUNS,
    random_seed: int = TOURNAMENT_SIMULATION_RANDOM_SEED,
) -> pd.DataFrame:
    rng = np.random.default_rng(random_seed)
    group_matches = world_cup_matches.assign(
        _match_id_sort=pd.to_numeric(world_cup_matches["match_id"]),
    ).sort_values("_match_id_sort")
    group_distributions = _group_scoreline_distributions(
        group_matches,
        team_strength,
        squad_strength,
        latest_fifa_rankings,
        external_player_strength,
        models,
    )
    group_tiebreak_strengths = _group_tiebreak_strengths(
        group_matches.rename(columns={"group_letter": "group"}),
        latest_fifa_rankings,
        external_player_strength,
        models,
    )
    slots = _normalise_knockout_slots(knockout_slots)
    sorted_slots = slots.assign(_match_id_sort=pd.to_numeric(slots["match_id"])).sort_values(
        "_match_id_sort"
    )

    teams = sorted(
        set(group_matches["home_team"].map(canonical_team_name).tolist())
        | set(group_matches["away_team"].map(canonical_team_name).tolist())
    )
    round_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    group_points_total: dict[str, float] = defaultdict(float)
    knockout_opponent_strength_total: dict[str, float] = defaultdict(float)
    knockout_opponent_match_total: dict[str, int] = defaultdict(int)
    title_route_opponent_strength_total: dict[str, float] = defaultdict(float)
    title_route_opponent_match_total: dict[str, int] = defaultdict(int)
    distribution_cache: dict[tuple[str, str], tuple[pd.DataFrame, float]] = {}

    for _ in range(simulation_runs):
        sampled_group_rows = []
        for row, distribution in zip(group_matches.itertuples(index=False), group_distributions):
            home_goals, away_goals = _sample_scoreline(distribution, rng)
            sampled_group_rows.append(
                {
                    "match_id": getattr(row, "match_id"),
                    "group": getattr(row, "group_letter"),
                    "home_team": canonical_team_name(getattr(row, "home_team")),
                    "away_team": canonical_team_name(getattr(row, "away_team")),
                    "predicted_home_goals": home_goals,
                    "predicted_away_goals": away_goals,
                    "winning_team": outcome_from_scores(home_goals, away_goals),
                }
            )

        sampled_group_predictions = pd.DataFrame(sampled_group_rows)
        standings = build_group_standings(
            sampled_group_predictions,
            group_tiebreak_strengths,
        )
        for standing_row in standings.itertuples(index=False):
            team_name = str(getattr(standing_row, "team"))
            group_points_total[team_name] += float(getattr(standing_row, "points"))
            if int(getattr(standing_row, "group_rank")) == 1:
                round_counts[team_name]["group_winner_count"] += 1

        match_results: dict[int, dict[str, str]] = {}
        used_third_groups: set[str] = set()
        route_opponents: dict[str, list[float]] = defaultdict(list)
        for slot_row in sorted_slots.drop(columns="_match_id_sort").itertuples(index=False):
            row_data = slot_row._asdict()
            match_id = int(row_data["match_id"])
            round_name = str(row_data["round"])
            predicted_home_team = resolve_knockout_slot(
                str(row_data["slot_home"]),
                standings,
                match_results,
                used_third_groups,
            )
            predicted_away_team = resolve_knockout_slot(
                str(row_data["slot_away"]),
                standings,
                match_results,
                used_third_groups,
            )
            _increment_reached_round(round_counts, predicted_home_team, round_name)
            _increment_reached_round(round_counts, predicted_away_team, round_name)
            home_opponent_strength = group_tiebreak_strengths[predicted_away_team]
            away_opponent_strength = group_tiebreak_strengths[predicted_home_team]
            knockout_opponent_strength_total[predicted_home_team] += home_opponent_strength
            knockout_opponent_strength_total[predicted_away_team] += away_opponent_strength
            knockout_opponent_match_total[predicted_home_team] += 1
            knockout_opponent_match_total[predicted_away_team] += 1
            route_opponents[predicted_home_team].append(home_opponent_strength)
            route_opponents[predicted_away_team].append(away_opponent_strength)

            result = _sample_knockout_result(
                predicted_home_team,
                predicted_away_team,
                team_strength,
                squad_strength,
                latest_fifa_rankings,
                external_player_strength,
                models,
                distribution_cache,
                rng,
            )
            match_results[match_id] = {
                "winner_team": str(result["winner_team"]),
                "loser_team": str(result["loser_team"]),
            }
            if round_name == "Final":
                champion = str(result["winner_team"])
                round_counts[champion]["champion_count"] += 1
                title_route_opponent_strength_total[champion] += sum(route_opponents[champion])
                title_route_opponent_match_total[champion] += len(route_opponents[champion])

    rows = []
    for team_name in teams:
        counts = round_counts[team_name]
        title_route_matches = title_route_opponent_match_total[team_name]
        knockout_route_matches = knockout_opponent_match_total[team_name]
        title_route_difficulty = (
            title_route_opponent_strength_total[team_name] / title_route_matches
            if title_route_matches
            else np.nan
        )
        knockout_route_difficulty = (
            knockout_opponent_strength_total[team_name] / knockout_route_matches
            if knockout_route_matches
            else np.nan
        )
        rows.append(
            {
                "team_name": team_name,
                "simulations": simulation_runs,
                "avg_group_points": round(
                    group_points_total[team_name] / simulation_runs,
                    3,
                ),
                "group_winner_probability": counts["group_winner_count"] / simulation_runs,
                "round_of_32_probability": counts["round_of_32_count"] / simulation_runs,
                "round_of_16_probability": counts["round_of_16_count"] / simulation_runs,
                "quarter_final_probability": counts["quarter_final_count"] / simulation_runs,
                "semi_final_probability": counts["semi_final_count"] / simulation_runs,
                "final_probability": counts["final_count"] / simulation_runs,
                "champion_probability": counts["champion_count"] / simulation_runs,
                "title_route_samples": counts["champion_count"],
                "avg_title_route_opponent_strength": title_route_difficulty,
                "avg_knockout_opponent_strength": knockout_route_difficulty,
            }
        )

    simulation = pd.DataFrame(rows)
    simulation["route_difficulty_raw"] = simulation[
        "avg_title_route_opponent_strength"
    ].fillna(simulation["avg_knockout_opponent_strength"])
    fallback_route_difficulty = simulation["route_difficulty_raw"].median()
    simulation["route_difficulty_raw"] = simulation["route_difficulty_raw"].fillna(
        0.0 if pd.isna(fallback_route_difficulty) else fallback_route_difficulty
    )
    route_minimum = simulation["route_difficulty_raw"].min()
    route_maximum = simulation["route_difficulty_raw"].max()
    if pd.isna(route_minimum) or route_minimum == route_maximum:
        simulation["route_difficulty_index"] = 50.0
    else:
        simulation["route_difficulty_index"] = (
            (simulation["route_difficulty_raw"] - route_minimum)
            / (route_maximum - route_minimum)
            * 100
        )
    return (
        simulation.round(
            {
                "avg_title_route_opponent_strength": 3,
                "avg_knockout_opponent_strength": 3,
                "route_difficulty_raw": 3,
                "route_difficulty_index": 1,
            }
        )
        .sort_values(
            ["champion_probability", "final_probability", "semi_final_probability", "team_name"],
            ascending=[False, False, False, True],
        )
        .reset_index(drop=True)
    )


def main() -> None:
    training_data = _load_table("main_features.features_historical_match_training")
    world_cup_matches = _load_table("main_staging.stg_group_fixtures")
    knockout_slots = _load_table("main_staging.stg_knockout_slots")
    team_strength = _load_table("main_marts.mart_team_strength")
    squad_strength = _load_table("main_marts.mart_squad_strength")
    latest_fifa_rankings = _load_table("main_marts.mart_latest_fifa_rankings")
    external_player_strength = _load_table("main_marts.mart_external_player_strength")
    team_event_profile = _load_table("main_marts.mart_team_event_profile")
    historical_results = _load_table("main_staging.stg_international_results")

    models, metrics = train_goal_models(training_data, historical_results)
    metrics["squad_overlay"] = {
        "enabled": True,
        "source_table": "main_marts.mart_squad_strength",
        "teams_with_squad_data": int(squad_strength["team_name"].nunique()),
        "goal_adjustment_cap": SQUAD_GOAL_ADJUSTMENT_CAP,
        "method": (
            "Conservative post-model expected-goals adjustment using squad experience, "
            "attacking star power, defensive experience, and overall star power z-scores."
        ),
    }
    metrics["event_predictions"] = {
        "enabled": True,
        "source_table": "main_marts.mart_team_event_profile",
        "teams_with_event_profiles": int(team_event_profile["team_name"].nunique()),
        "international_event_matches": int(
            team_event_profile["international_event_matches"].sum()
        ),
        "matched_club_players": int(team_event_profile["matched_club_players"].sum()),
        "method": (
            "Corners use weighted international team event rates. Yellow and red cards "
            "blend international team rates with 2025/26 top-five-league club player "
            "discipline where squad players can be matched."
        ),
    }
    metrics["fifa_rankings"] = {
        "enabled": True,
        "source_table": "main_marts.mart_latest_fifa_rankings",
        "latest_ranking_date": str(latest_fifa_rankings["ranking_date"].max()),
        "teams_with_latest_rankings": int(latest_fifa_rankings["team_name"].nunique()),
    }
    metrics["external_match_features"] = {
        "enabled": True,
        "source_table": "main_staging.stg_international_match_features",
        "current_player_strength_table": "main_marts.mart_external_player_strength",
        "historical_rows_with_external_features": int(
            training_data["has_external_match_features"].sum()
        ),
        "teams_with_current_player_strength": int(
            external_player_strength["team_name"].nunique()
        ),
        "method": (
            "Outcome model receives historical external Elo, EA Sports/FIFA player "
            "aggregate ratings, and form features where matched. Missing historical "
            "features use training-set medians; 2026 scoring uses the latest player "
            "aggregate snapshot."
        ),
    }
    group_predictions = predict_world_cup_group_matches(
        world_cup_matches,
        team_strength,
        squad_strength,
        latest_fifa_rankings,
        external_player_strength,
        team_event_profile,
        models,
    )
    knockout_predictions = predict_world_cup_knockout_matches(
        knockout_slots,
        group_predictions,
        team_strength,
        squad_strength,
        latest_fifa_rankings,
        external_player_strength,
        team_event_profile,
        models,
    )
    predictions = build_model_predictions(group_predictions, knockout_predictions)
    model_team_features = build_model_team_features(team_strength, models)
    tournament_simulation = simulate_tournament_probabilities(
        world_cup_matches,
        knockout_slots,
        team_strength,
        squad_strength,
        latest_fifa_rankings,
        external_player_strength,
        models,
    )
    simulation_favorite = tournament_simulation.iloc[0]
    metrics["tournament_simulation"] = {
        "enabled": True,
        "simulation_runs": TOURNAMENT_SIMULATION_RUNS,
        "random_seed": TOURNAMENT_SIMULATION_RANDOM_SEED,
        "method": (
            "Repeated tournament simulation samples group-stage scorelines and dynamic "
            "knockout matchups from the calibrated scoreline probability grid. This "
            "estimates advancement probabilities, championship probabilities, and route "
            "difficulty without changing the single deterministic submission bracket."
        ),
        "championship_favorite": str(simulation_favorite["team_name"]),
        "championship_favorite_probability": float(
            simulation_favorite["champion_probability"]
        ),
    }

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_GROUP_PREDICTIONS_V2_PATH.write_text(
        group_predictions.to_csv(index=False),
        encoding="utf-8",
    )
    MODEL_KNOCKOUT_PREDICTIONS_V2_PATH.write_text(
        knockout_predictions.to_csv(index=False),
        encoding="utf-8",
    )
    MODEL_PREDICTIONS_V2_PATH.write_text(
        predictions.to_csv(index=False),
        encoding="utf-8",
    )
    MODEL_TEAM_FEATURES_V2_PATH.write_text(
        model_team_features.to_csv(index=False),
        encoding="utf-8",
    )
    MODEL_TOURNAMENT_SIMULATION_V2_PATH.write_text(
        tournament_simulation.to_csv(index=False),
        encoding="utf-8",
    )
    MODEL_METRICS_V2_PATH.write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    print(f"Selected model: {metrics['selected_model_type']}")
    print(f"Selected outcome model: {metrics['selected_outcome_model_type']}")
    print(f"Training rows: {metrics['training']['rows']:,}")
    print(f"Holdout rows: {metrics['holdout']['rows']:,}")
    print(f"Tournament calibration rows: {metrics['tournament_calibration']['rows']:,}")
    print(f"Selected draw threshold: {metrics['draw_probability_threshold']:.2f}")
    print(
        "Selected scoreline/outcome blend weight: "
        f"{metrics['scoreline_outcome_blend_weight']:.2f}"
    )
    print(f"Holdout home goals MAE: {metrics['holdout']['home_goals_mae']:.3f}")
    print(f"Holdout away goals MAE: {metrics['holdout']['away_goals_mae']:.3f}")
    print(f"Holdout average goals MAE: {metrics['holdout']['average_goals_mae']:.3f}")
    print(
        "Holdout rounded outcome accuracy: "
        f"{metrics['holdout']['rounded_match_outcome_accuracy']:.3f}"
    )
    print(
        "Holdout direct outcome accuracy: "
        f"{metrics['outcome_holdout']['accuracy']:.3f}"
    )
    print(
        "Holdout blended scoreline outcome accuracy: "
        f"{metrics['reconciled_holdout']['match_outcome_accuracy']:.3f}"
    )
    print(
        "Holdout blended exact score accuracy: "
        f"{metrics['reconciled_holdout']['exact_score_accuracy']:.3f}"
    )
    print(f"Wrote group predictions to {MODEL_GROUP_PREDICTIONS_V2_PATH}")
    print(f"Wrote knockout predictions to {MODEL_KNOCKOUT_PREDICTIONS_V2_PATH}")
    print(f"Wrote combined predictions to {MODEL_PREDICTIONS_V2_PATH}")
    print(f"Wrote team model features to {MODEL_TEAM_FEATURES_V2_PATH}")
    print(f"Wrote tournament simulation to {MODEL_TOURNAMENT_SIMULATION_V2_PATH}")
    print(f"Wrote metrics to {MODEL_METRICS_V2_PATH}")


if __name__ == "__main__":
    main()
