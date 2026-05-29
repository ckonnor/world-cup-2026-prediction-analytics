from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import kagglehub
import pandas as pd

from world_cup.paths import (
    EXTERNAL_RAW_DIR,
    TRANSFERMARKT_APPEARANCES_PATH,
    TRANSFERMARKT_COMPETITIONS_PATH,
    TRANSFERMARKT_PLAYERS_PATH,
)


KAGGLE_TRANSFERMARKT_DATASET = "davidcariboo/player-scores"
KAGGLE_TRANSFERMARKT_SOURCE_URL = (
    "https://www.kaggle.com/datasets/davidcariboo/player-scores"
)


def _copy_source_csv(source_file: Path, destination_file: Path) -> pd.DataFrame:
    if not source_file.exists():
        raise FileNotFoundError(f"Expected Kaggle source file not found: {source_file}")

    frame = pd.read_csv(source_file)
    frame["source_dataset"] = KAGGLE_TRANSFERMARKT_DATASET
    frame["source_url"] = KAGGLE_TRANSFERMARKT_SOURCE_URL
    frame["downloaded_at_utc"] = datetime.now(UTC).replace(microsecond=0).isoformat()
    frame.to_csv(destination_file, index=False)
    return frame


def download_transfermarkt_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dataset_path = Path(kagglehub.dataset_download(KAGGLE_TRANSFERMARKT_DATASET))
    EXTERNAL_RAW_DIR.mkdir(parents=True, exist_ok=True)

    appearances = _copy_source_csv(
        dataset_path / "appearances.csv",
        TRANSFERMARKT_APPEARANCES_PATH,
    )
    competitions = _copy_source_csv(
        dataset_path / "competitions.csv",
        TRANSFERMARKT_COMPETITIONS_PATH,
    )
    players = _copy_source_csv(
        dataset_path / "players.csv",
        TRANSFERMARKT_PLAYERS_PATH,
    )
    return appearances, competitions, players


def main() -> None:
    appearances, competitions, players = download_transfermarkt_data()
    print(f"- wrote {len(appearances):,} rows to {TRANSFERMARKT_APPEARANCES_PATH}")
    print(f"- wrote {len(competitions):,} rows to {TRANSFERMARKT_COMPETITIONS_PATH}")
    print(f"- wrote {len(players):,} rows to {TRANSFERMARKT_PLAYERS_PATH}")


if __name__ == "__main__":
    main()
