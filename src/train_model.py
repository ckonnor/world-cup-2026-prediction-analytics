from __future__ import annotations

import json
from dataclasses import dataclass

import duckdb
import numpy as np
import pandas as pd
from sklearn.linear_model import PoissonRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from world_cup.paths import (
    DUCKDB_PATH,
    MODEL_GROUP_PREDICTIONS_V1_PATH,
    MODEL_METRICS_V1_PATH,
    PROCESSED_DIR,
)


FEATURE_COLUMNS = [
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

WORLD_CUP_FEATURE_RENAME = {
    "home_last_10_points_per_match": "home_prior_10_points_per_match",
    "away_last_10_points_per_match": "away_prior_10_points_per_match",
    "home_last_10_goal_diff_per_match": "home_prior_10_goal_diff_per_match",
    "away_last_10_goal_diff_per_match": "away_prior_10_goal_diff_per_match",
    "home_last_10_goals_for_per_match": "home_prior_10_goals_for_per_match",
    "away_last_10_goals_for_per_match": "away_prior_10_goals_for_per_match",
    "home_last_10_goals_against_per_match": "home_prior_10_goals_against_per_match",
    "away_last_10_goals_against_per_match": "away_prior_10_goals_against_per_match",
    "last_10_points_per_match_diff": "prior_10_points_per_match_diff",
    "last_10_goal_diff_per_match_diff": "prior_10_goal_diff_per_match_diff",
    "last_10_goals_for_per_match_diff": "prior_10_goals_for_per_match_diff",
    "last_10_goals_against_per_match_diff": "prior_10_goals_against_per_match_diff",
}


@dataclass(frozen=True)
class TrainedGoalModels:
    home_model: Pipeline
    away_model: Pipeline
    feature_medians: pd.Series


def _load_table(table_name: str) -> pd.DataFrame:
    if not DUCKDB_PATH.exists():
        raise FileNotFoundError(
            f"{DUCKDB_PATH} does not exist. Run dbt build before training the model."
        )

    with duckdb.connect(str(DUCKDB_PATH), read_only=True) as con:
        return con.execute(f"select * from {table_name}").fetchdf()


def _prepare_training_features(data: pd.DataFrame) -> pd.DataFrame:
    features = data[FEATURE_COLUMNS].copy()
    features["neutral"] = features["neutral"].astype(int)
    return features


def _fit_poisson_model(features: pd.DataFrame, target: pd.Series) -> Pipeline:
    model = Pipeline(
        steps=[
            ("scale", StandardScaler()),
            ("poisson", PoissonRegressor(alpha=0.1, max_iter=1000)),
        ]
    )
    model.fit(features, target)
    return model


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


def train_goal_models(training_data: pd.DataFrame) -> tuple[TrainedGoalModels, dict[str, object]]:
    model_data = training_data.dropna(subset=FEATURE_COLUMNS + ["home_score", "away_score"]).copy()
    model_data["match_date"] = pd.to_datetime(model_data["match_date"])

    holdout_start = pd.Timestamp("2022-01-01")
    train = model_data[model_data["match_date"] < holdout_start]
    holdout = model_data[model_data["match_date"] >= holdout_start]

    if train.empty or holdout.empty:
        raise ValueError("Training and holdout sets must both contain rows.")

    train_features = _prepare_training_features(train)
    holdout_features = _prepare_training_features(holdout)

    home_model = _fit_poisson_model(train_features, train["home_score"])
    away_model = _fit_poisson_model(train_features, train["away_score"])

    metrics = {
        "model_type": "PoissonRegressor with StandardScaler",
        "holdout_start": str(holdout_start.date()),
        "feature_columns": FEATURE_COLUMNS,
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
        "notes": [
            "Scores are predicted from team-form features only.",
            "Corners and card predictions remain simple constants because the current source data does not include historical corners/cards.",
            "Rows with missing 2026 team-strength features use training-set median feature values as a fallback.",
        ],
    }

    return (
        TrainedGoalModels(
            home_model=home_model,
            away_model=away_model,
            feature_medians=train_features.median(numeric_only=True),
        ),
        metrics,
    )


def _prepare_world_cup_features(
    world_cup_matches: pd.DataFrame,
    feature_medians: pd.Series,
) -> pd.DataFrame:
    features = world_cup_matches.rename(columns=WORLD_CUP_FEATURE_RENAME).copy()
    features["neutral"] = 1
    features = features[FEATURE_COLUMNS]
    return features.fillna(feature_medians)


def predict_world_cup_group_matches(
    world_cup_matches: pd.DataFrame,
    models: TrainedGoalModels,
) -> pd.DataFrame:
    features = _prepare_world_cup_features(world_cup_matches, models.feature_medians)
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


def main() -> None:
    training_data = _load_table("main_features.features_historical_match_training")
    world_cup_matches = _load_table("main_features.features_world_cup_group_matches")

    models, metrics = train_goal_models(training_data)
    group_predictions = predict_world_cup_group_matches(world_cup_matches, models)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_GROUP_PREDICTIONS_V1_PATH.write_text(
        group_predictions.to_csv(index=False),
        encoding="utf-8",
    )
    MODEL_METRICS_V1_PATH.write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    print(f"Training rows: {metrics['training']['rows']:,}")
    print(f"Holdout rows: {metrics['holdout']['rows']:,}")
    print(f"Holdout home goals MAE: {metrics['holdout']['home_goals_mae']:.3f}")
    print(f"Holdout away goals MAE: {metrics['holdout']['away_goals_mae']:.3f}")
    print(
        "Holdout rounded outcome accuracy: "
        f"{metrics['holdout']['rounded_match_outcome_accuracy']:.3f}"
    )
    print(f"Wrote group predictions to {MODEL_GROUP_PREDICTIONS_V1_PATH}")
    print(f"Wrote metrics to {MODEL_METRICS_V1_PATH}")


if __name__ == "__main__":
    main()
