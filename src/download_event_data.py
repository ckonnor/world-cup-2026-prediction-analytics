from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
import re
import unicodedata

import kagglehub
import pandas as pd
import requests

from world_cup.paths import (
    CLUB_PLAYER_STATS_PATH,
    EXTERNAL_RAW_DIR,
    FOOTYSTATS_MATCH_STATS_PATH,
)


FOOTYSTATS_BASE_URL = "https://footystats.org/c-dl.php"
KAGGLE_PLAYER_DATASET = "hubertsidorowicz/football-players-stats-2025-2026"
KAGGLE_SOURCE_URL = (
    "https://www.kaggle.com/datasets/hubertsidorowicz/"
    "football-players-stats-2025-2026"
)


@dataclass(frozen=True)
class FootyStatsCompetition:
    competition_name: str
    comp_id: int
    source_type: str
    source_weight: float


FOOTYSTATS_COMPETITIONS = [
    FootyStatsCompetition("WC Qualification CONCACAF 2026", 11426, "qualification", 1.00),
    FootyStatsCompetition("WC Qualification Asia 2026", 10117, "qualification", 1.00),
    FootyStatsCompetition("WC Qualification Europe 2026", 13964, "qualification", 1.00),
    FootyStatsCompetition("WC Qualification Africa 2026", 12061, "qualification", 1.00),
    FootyStatsCompetition("WC Qualification South America 2026", 10121, "qualification", 1.00),
    FootyStatsCompetition("WC Qualification Intercontinental 2026", 16451, "qualification", 1.00),
    FootyStatsCompetition("FIFA World Cup 2022", 7432, "world_cup", 0.80),
    FootyStatsCompetition("FIFA World Cup 2018", 1425, "world_cup", 0.55),
    FootyStatsCompetition("FIFA World Cup 2014", 1384, "world_cup", 0.35),
    FootyStatsCompetition("FIFA World Cup 2010", 1389, "world_cup", 0.25),
]


def _download_footystats_csv(comp_id: int, csv_type: str) -> pd.DataFrame:
    response = requests.get(
        FOOTYSTATS_BASE_URL,
        params={"comp": comp_id, "type": csv_type},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text))


def _parse_footystats_date(value: object) -> pd.Timestamp:
    date_text = str(value).replace(" - ", " ")
    return pd.to_datetime(date_text, format="%b %d %Y %I:%M%p", errors="coerce")


def _numeric_column(frame: pd.DataFrame, column_name: str) -> pd.Series:
    return pd.to_numeric(frame[column_name], errors="coerce")


def _build_match_rows(source: FootyStatsCompetition, downloaded_at_utc: str) -> pd.DataFrame:
    raw = _download_footystats_csv(source.comp_id, "matches")
    source_url = f"{FOOTYSTATS_BASE_URL}?comp={source.comp_id}&type=matches"
    match_dates = raw["date_GMT"].map(_parse_footystats_date)

    frame = pd.DataFrame(
        {
            "source_competition": source.competition_name,
            "source_type": source.source_type,
            "source_weight": source.source_weight,
            "comp_id": source.comp_id,
            "source_url": source_url,
            "downloaded_at_utc": downloaded_at_utc,
            "source_row_number": range(1, len(raw) + 1),
            "match_date_gmt_raw": raw["date_GMT"],
            "match_date": match_dates.dt.date.astype("string"),
            "status": raw["status"],
            "home_team_name": raw["home_team_name"],
            "away_team_name": raw["away_team_name"],
            "home_goals": _numeric_column(raw, "home_team_goal_count"),
            "away_goals": _numeric_column(raw, "away_team_goal_count"),
            "home_corners": _numeric_column(raw, "home_team_corner_count"),
            "away_corners": _numeric_column(raw, "away_team_corner_count"),
            "home_yellow_cards": _numeric_column(raw, "home_team_yellow_cards"),
            "away_yellow_cards": _numeric_column(raw, "away_team_yellow_cards"),
            "home_red_cards": _numeric_column(raw, "home_team_red_cards"),
            "away_red_cards": _numeric_column(raw, "away_team_red_cards"),
        }
    )
    frame["source_match_id"] = (
        frame["comp_id"].astype(str) + "-" + frame["source_row_number"].astype(str)
    )
    return frame


def download_footystats_match_stats() -> pd.DataFrame:
    downloaded_at_utc = datetime.now(UTC).replace(microsecond=0).isoformat()
    frames = [
        _build_match_rows(source, downloaded_at_utc)
        for source in FOOTYSTATS_COMPETITIONS
    ]
    combined = pd.concat(frames, ignore_index=True)
    combined.to_csv(FOOTYSTATS_MATCH_STATS_PATH, index=False)
    return combined


def _player_name_key(value: object) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value))
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", ascii_text.casefold()).split())


def _fifa_country_code(value: object) -> str:
    parts = str(value).split()
    if not parts:
        return ""
    return parts[-1].upper()


def download_club_player_stats() -> pd.DataFrame:
    dataset_path = Path(kagglehub.dataset_download(KAGGLE_PLAYER_DATASET))
    source_file = dataset_path / "players_data_light-2025_2026.csv"
    if not source_file.exists():
        raise FileNotFoundError(f"Expected Kaggle source file not found: {source_file}")

    raw = pd.read_csv(source_file)
    downloaded_at_utc = datetime.now(UTC).replace(microsecond=0).isoformat()
    frame = pd.DataFrame(
        {
            "source_dataset": KAGGLE_PLAYER_DATASET,
            "source_url": KAGGLE_SOURCE_URL,
            "downloaded_at_utc": downloaded_at_utc,
            "player_name": raw["Player"],
            "player_name_key": raw["Player"].map(_player_name_key),
            "nation_raw": raw["Nation"],
            "nation_code": raw["Nation"].map(_fifa_country_code),
            "positions": raw["Pos"],
            "club_name": raw["Squad"],
            "competition": raw["Comp"],
            "age": pd.to_numeric(raw["Age"], errors="coerce"),
            "matches_played": pd.to_numeric(raw["MP"], errors="coerce"),
            "starts": pd.to_numeric(raw["Starts"], errors="coerce"),
            "minutes": pd.to_numeric(raw["Min"], errors="coerce"),
            "nineties": pd.to_numeric(raw["90s"], errors="coerce"),
            "goals": pd.to_numeric(raw["Gls"], errors="coerce"),
            "assists": pd.to_numeric(raw["Ast"], errors="coerce"),
            "yellow_cards": pd.to_numeric(raw["CrdY"], errors="coerce"),
            "red_cards": pd.to_numeric(raw["CrdR"], errors="coerce"),
            "second_yellow_cards": pd.to_numeric(raw["2CrdY"], errors="coerce"),
            "fouls_committed": pd.to_numeric(raw["Fls"], errors="coerce"),
            "fouls_drawn": pd.to_numeric(raw["Fld"], errors="coerce"),
            "crosses": pd.to_numeric(raw["Crs"], errors="coerce"),
            "tackles_won": pd.to_numeric(raw["TklW"], errors="coerce"),
            "interceptions": pd.to_numeric(raw["Int"], errors="coerce"),
        }
    )
    frame.to_csv(CLUB_PLAYER_STATS_PATH, index=False)
    return frame


def main() -> None:
    EXTERNAL_RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("Downloading FootyStats match event data...")
    match_stats = download_footystats_match_stats()
    print(f"- wrote {len(match_stats):,} rows to {FOOTYSTATS_MATCH_STATS_PATH}")

    print("Downloading KaggleHub club player discipline data...")
    player_stats = download_club_player_stats()
    print(f"- wrote {len(player_stats):,} rows to {CLUB_PLAYER_STATS_PATH}")


if __name__ == "__main__":
    main()
