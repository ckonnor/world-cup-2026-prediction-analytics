from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import kagglehub
import pandas as pd

from world_cup.paths import (
    EXTERNAL_RAW_DIR,
    INTERNATIONAL_MATCH_FEATURES_PATH,
    INTERNATIONAL_PLAYER_AGGREGATES_PATH,
)


KAGGLE_MATCH_FEATURE_DATASET = "lchikry/international-football-match-features-and-statistics"
KAGGLE_MATCH_FEATURE_SOURCE_URL = (
    "https://www.kaggle.com/datasets/lchikry/"
    "international-football-match-features-and-statistics"
)


def _copy_source_csv(source_file: Path, destination_file: Path) -> pd.DataFrame:
    if not source_file.exists():
        raise FileNotFoundError(f"Expected Kaggle source file not found: {source_file}")

    frame = pd.read_csv(source_file)
    frame["source_dataset"] = KAGGLE_MATCH_FEATURE_DATASET
    frame["source_url"] = KAGGLE_MATCH_FEATURE_SOURCE_URL
    frame["downloaded_at_utc"] = datetime.now(UTC).replace(microsecond=0).isoformat()
    frame.to_csv(destination_file, index=False)
    return frame


def download_match_feature_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    dataset_path = Path(kagglehub.dataset_download(KAGGLE_MATCH_FEATURE_DATASET))
    EXTERNAL_RAW_DIR.mkdir(parents=True, exist_ok=True)

    match_features = _copy_source_csv(
        dataset_path / "teams_match_features.csv",
        INTERNATIONAL_MATCH_FEATURES_PATH,
    )
    player_aggregates = _copy_source_csv(
        dataset_path / "player_aggregates.csv",
        INTERNATIONAL_PLAYER_AGGREGATES_PATH,
    )
    return match_features, player_aggregates


def main() -> None:
    match_features, player_aggregates = download_match_feature_data()
    print(f"- wrote {len(match_features):,} rows to {INTERNATIONAL_MATCH_FEATURES_PATH}")
    print(f"- wrote {len(player_aggregates):,} rows to {INTERNATIONAL_PLAYER_AGGREGATES_PATH}")


if __name__ == "__main__":
    main()
