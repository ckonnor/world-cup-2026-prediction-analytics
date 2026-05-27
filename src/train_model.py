from __future__ import annotations

import json
import math
import unicodedata
from dataclasses import dataclass
from typing import Callable

import duckdb
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import PoissonRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from world_cup.baseline import build_group_standings, resolve_knockout_slot
from world_cup.paths import (
    DUCKDB_PATH,
    MODEL_GROUP_PREDICTIONS_V2_PATH,
    MODEL_KNOCKOUT_PREDICTIONS_V2_PATH,
    MODEL_METRICS_V2_PATH,
    MODEL_PREDICTIONS_V2_PATH,
    PROCESSED_DIR,
)


BASE_FEATURE_COLUMNS = [
    "neutral",
    "home_prior_10_points_per_match",
    "away_prior_10_points_per_match",
    "home_prior_10_goal_diff_per_match",
    "away_prior_10_goal_diff_per_match",
    "home_prior_10_goals_for_per_match",
    "away_prior_10_goals_for_per_match",
    "home_prior_10_goals_against_per_match",
    "away_prior_10_goals_against_per_match",
    "prior_10_points_per_match_diff",
    "prior_10_goal_diff_per_match_diff",
    "prior_10_goals_for_per_match_diff",
    "prior_10_goals_against_per_match_diff",
]

ELO_FEATURE_COLUMNS = [
    "home_pre_match_elo",
    "away_pre_match_elo",
    "pre_match_elo_diff",
    "home_elo_expected_result",
]

FEATURE_COLUMNS = [*BASE_FEATURE_COLUMNS, *ELO_FEATURE_COLUMNS]

HOST_TEAMS = {"Canada", "Mexico", "United States"}
TEAM_NAME_ALIASES = {
    "usa": "United States",
    "cabo verde": "Cape Verde",
    "cote d'ivoire": "Ivory Coast",
    "czechia": "Czech Republic",
    "turkiye": "Turkey",
    "congo dr": "DR Congo",
}
DEFAULT_ELO = 1500.0
HOME_ADVANTAGE_ELO = 60.0


@dataclass(frozen=True)
class ModelSpec:
    name: str
    factory: Callable[[], object]


@dataclass(frozen=True)
class TrainedGoalModels:
    home_model: object
    away_model: object
    feature_medians: pd.Series
    current_elo_ratings: dict[str, float]
    selected_model_name: str


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


def _prepare_training_features(data: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    features = data[feature_columns].copy()
    features["neutral"] = features["neutral"].astype(int)
    return features


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


def _rounded_goals(predictions: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(predictions), 0, 8).astype(int)


def outcome_from_scores(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home"
    if away_goals > home_goals:
        return "away"
    return "draw"


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


def _fit_and_score_spec(
    spec: ModelSpec,
    train: pd.DataFrame,
    holdout: pd.DataFrame,
) -> tuple[object, object, dict[str, object]]:
    train_features = _prepare_training_features(train, FEATURE_COLUMNS)
    holdout_features = _prepare_training_features(holdout, FEATURE_COLUMNS)

    home_model = spec.factory()
    away_model = spec.factory()
    home_model.fit(train_features, train["home_score"])
    away_model.fit(train_features, train["away_score"])

    metrics = {
        "model_type": spec.name,
        "training": _score_predictions(
            train,
            home_model.predict(train_features),
            away_model.predict(train_features),
        ),
        "holdout": _score_predictions(
            holdout,
            home_model.predict(holdout_features),
            away_model.predict(holdout_features),
        ),
    }
    return home_model, away_model, metrics


def train_goal_models(
    training_data: pd.DataFrame,
    historical_results: pd.DataFrame,
) -> tuple[TrainedGoalModels, dict[str, object]]:
    elo_features, current_elo_ratings = build_elo_features(historical_results)
    model_data = training_data.merge(elo_features, on="result_id", how="inner")
    model_data = model_data.dropna(subset=FEATURE_COLUMNS + ["home_score", "away_score"]).copy()
    model_data["match_date"] = pd.to_datetime(model_data["match_date"])

    holdout_start = pd.Timestamp("2022-01-01")
    train = model_data[model_data["match_date"] < holdout_start]
    holdout = model_data[model_data["match_date"] >= holdout_start]

    if train.empty or holdout.empty:
        raise ValueError("Training and holdout sets must both contain rows.")

    candidate_results = []
    for spec in _model_specs():
        home_model, away_model, metrics = _fit_and_score_spec(spec, train, holdout)
        candidate_results.append((home_model, away_model, metrics))

    selected_home_model, selected_away_model, selected_metrics = min(
        candidate_results,
        key=lambda item: item[2]["holdout"]["average_goals_mae"],
    )
    train_features = _prepare_training_features(train, FEATURE_COLUMNS)

    metrics = {
        "model_version": "v2",
        "selected_model_type": selected_metrics["model_type"],
        "selection_metric": "holdout.average_goals_mae",
        "holdout_start": str(holdout_start.date()),
        "feature_columns": FEATURE_COLUMNS,
        "candidate_models": [result[2] for result in candidate_results],
        "training": selected_metrics["training"],
        "holdout": selected_metrics["holdout"],
        "notes": [
            "V2 adds pre-match Elo features computed from historical international results.",
            "The script compares Poisson regression and histogram gradient boosting with Poisson loss.",
            "dbt resolves known playoff placeholders and exposes model team names for joining to historical source names.",
            "Knockout predictions are resolved from the model-driven group standings and predicted sequentially through the bracket.",
            "Corners and card predictions remain simple constants because the current source data does not include historical corners/cards.",
            "Rows with missing 2026 team-strength or Elo features use training-set median values as a fallback.",
        ],
    }

    return (
        TrainedGoalModels(
            home_model=selected_home_model,
            away_model=selected_away_model,
            feature_medians=train_features.median(numeric_only=True),
            current_elo_ratings=current_elo_ratings,
            selected_model_name=selected_metrics["model_type"],
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


def _elo_rating(team_name: object, models: TrainedGoalModels) -> float:
    return float(models.current_elo_ratings.get(canonical_team_name(team_name), DEFAULT_ELO))


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
    models: TrainedGoalModels,
) -> pd.DataFrame:
    strength_lookup = _team_strength_lookup(team_strength)
    rows = []

    for row in matches.itertuples(index=False):
        home_team = _row_team_name_for_model(row, "home")
        away_team = _row_team_name_for_model(row, "away")
        home_elo = _elo_rating(home_team, models)
        away_elo = _elo_rating(away_team, models)
        neutral = _is_neutral_world_cup_match(home_team, away_team)

        home_points = _team_metric(home_team, "last_10_points_per_match", strength_lookup)
        away_points = _team_metric(away_team, "last_10_points_per_match", strength_lookup)
        home_goal_diff = _team_metric(home_team, "last_10_goal_diff_per_match", strength_lookup)
        away_goal_diff = _team_metric(away_team, "last_10_goal_diff_per_match", strength_lookup)
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

        rows.append(
            {
                "neutral": neutral,
                "home_prior_10_points_per_match": home_points,
                "away_prior_10_points_per_match": away_points,
                "home_prior_10_goal_diff_per_match": home_goal_diff,
                "away_prior_10_goal_diff_per_match": away_goal_diff,
                "home_prior_10_goals_for_per_match": home_goals_for,
                "away_prior_10_goals_for_per_match": away_goals_for,
                "home_prior_10_goals_against_per_match": home_goals_against,
                "away_prior_10_goals_against_per_match": away_goals_against,
                "prior_10_points_per_match_diff": home_points - away_points,
                "prior_10_goal_diff_per_match_diff": home_goal_diff - away_goal_diff,
                "prior_10_goals_for_per_match_diff": home_goals_for - away_goals_for,
                "prior_10_goals_against_per_match_diff": home_goals_against
                - away_goals_against,
                "home_pre_match_elo": home_elo,
                "away_pre_match_elo": away_elo,
                "pre_match_elo_diff": home_elo - away_elo,
                "home_elo_expected_result": _elo_expected_score(
                    home_elo,
                    away_elo,
                    bool(neutral),
                ),
            }
        )

    features = pd.DataFrame(rows)
    features = features[FEATURE_COLUMNS]
    return features.fillna(models.feature_medians)


def predict_world_cup_group_matches(
    world_cup_matches: pd.DataFrame,
    team_strength: pd.DataFrame,
    models: TrainedGoalModels,
) -> pd.DataFrame:
    features = _prepare_world_cup_match_features(world_cup_matches, team_strength, models)
    home_expected_goals = models.home_model.predict(features)
    away_expected_goals = models.away_model.predict(features)
    predicted_home_goals = _rounded_goals(home_expected_goals)
    predicted_away_goals = _rounded_goals(away_expected_goals)

    predictions = world_cup_matches[
        ["match_id", "group_letter", "home_team", "away_team", "match_date_utc", "venue"]
    ].copy()
    predictions = predictions.rename(columns={"group_letter": "group", "match_date_utc": "date_utc"})
    predictions["date_utc"] = pd.to_datetime(predictions["date_utc"]).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    predictions["predicted_home_goals"] = predicted_home_goals
    predictions["predicted_away_goals"] = predicted_away_goals
    predictions["corners"] = 9
    predictions["yellow_cards"] = 4
    predictions["red_cards"] = 0
    predictions["winning_team"] = [
        outcome_from_scores(int(home), int(away))
        for home, away in zip(predicted_home_goals, predicted_away_goals)
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
    models: TrainedGoalModels,
) -> tuple[np.ndarray, np.ndarray]:
    features = _prepare_world_cup_match_features(matches, team_strength, models)
    return models.home_model.predict(features), models.away_model.predict(features)


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
    models: TrainedGoalModels,
) -> pd.DataFrame:
    slots = _normalise_knockout_slots(knockout_slots)
    standings = build_group_standings(group_predictions)
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
            models,
        )
        home_goals = int(_rounded_goals(home_expected_goals)[0])
        away_goals = int(_rounded_goals(away_expected_goals)[0])
        match_winner, penalties = _knockout_match_winner(
            predicted_home_team,
            predicted_away_team,
            home_goals,
            away_goals,
            float(home_expected_goals[0]),
            float(away_expected_goals[0]),
            models,
        )
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
                "corners": 9,
                "yellow_cards": 4,
                "red_cards": 0,
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


def main() -> None:
    training_data = _load_table("main_features.features_historical_match_training")
    world_cup_matches = _load_table("main_staging.stg_group_fixtures")
    knockout_slots = _load_table("main_staging.stg_knockout_slots")
    team_strength = _load_table("main_marts.mart_team_strength")
    historical_results = _load_table("main_staging.stg_international_results")

    models, metrics = train_goal_models(training_data, historical_results)
    group_predictions = predict_world_cup_group_matches(world_cup_matches, team_strength, models)
    knockout_predictions = predict_world_cup_knockout_matches(
        knockout_slots,
        group_predictions,
        team_strength,
        models,
    )
    predictions = build_model_predictions(group_predictions, knockout_predictions)

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
    MODEL_METRICS_V2_PATH.write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    print(f"Selected model: {metrics['selected_model_type']}")
    print(f"Training rows: {metrics['training']['rows']:,}")
    print(f"Holdout rows: {metrics['holdout']['rows']:,}")
    print(f"Holdout home goals MAE: {metrics['holdout']['home_goals_mae']:.3f}")
    print(f"Holdout away goals MAE: {metrics['holdout']['away_goals_mae']:.3f}")
    print(f"Holdout average goals MAE: {metrics['holdout']['average_goals_mae']:.3f}")
    print(
        "Holdout rounded outcome accuracy: "
        f"{metrics['holdout']['rounded_match_outcome_accuracy']:.3f}"
    )
    print(f"Wrote group predictions to {MODEL_GROUP_PREDICTIONS_V2_PATH}")
    print(f"Wrote knockout predictions to {MODEL_KNOCKOUT_PREDICTIONS_V2_PATH}")
    print(f"Wrote combined predictions to {MODEL_PREDICTIONS_V2_PATH}")
    print(f"Wrote metrics to {MODEL_METRICS_V2_PATH}")


if __name__ == "__main__":
    main()
