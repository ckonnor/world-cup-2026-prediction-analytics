from __future__ import annotations

import re
from datetime import datetime, timezone
from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from world_cup.paths import EXTERNAL_RAW_DIR, WORLD_CUP_SQUADS_PATH


SQUADS_URL = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads"
USER_AGENT = "world-cup-analytics-project/0.1 (learning project)"
REQUIRED_COLUMNS = {"Pos.", "Player", "Date of birth (age)", "Caps", "Goals", "Club"}


def _clean_player_name(value: object) -> tuple[str, bool]:
    player_name = str(value).strip()
    is_captain = bool(re.search(r"\(captain\)", player_name, flags=re.IGNORECASE))
    player_name = re.sub(r"\s*\(captain\)", "", player_name, flags=re.IGNORECASE).strip()
    return player_name, is_captain


def _extract_birth_date(value: object) -> str | None:
    text = str(value)
    date_text = re.sub(r"\s*\(aged [0-9]+\)", "", text).strip()
    parsed = pd.to_datetime(date_text, errors="coerce")
    if pd.isna(parsed):
        return None
    return str(parsed.date())


def _extract_age(value: object) -> int | None:
    match = re.search(r"aged ([0-9]+)", str(value))
    if not match:
        return None
    return int(match.group(1))


def _normalise_table(table: pd.DataFrame, team_name: str, downloaded_at_utc: str) -> pd.DataFrame:
    frame = table.copy()
    frame.columns = [str(column).strip() for column in frame.columns]
    frame = frame[[column for column in frame.columns if not column.startswith("Unnamed")]]

    if not REQUIRED_COLUMNS.issubset(frame.columns):
        missing = ", ".join(sorted(REQUIRED_COLUMNS - set(frame.columns)))
        raise ValueError(f"Squad table for {team_name} is missing columns: {missing}")

    frame = frame.rename(
        columns={
            "No.": "shirt_number",
            "Pos.": "position",
            "Player": "player_name",
            "Date of birth (age)": "date_of_birth_age",
            "Caps": "caps",
            "Goals": "goals",
            "Club": "club",
        }
    )
    if "shirt_number" not in frame.columns:
        frame["shirt_number"] = None

    cleaned_players = frame["player_name"].map(_clean_player_name)
    frame["player_name"] = cleaned_players.map(lambda value: value[0])
    frame["is_captain"] = cleaned_players.map(lambda value: value[1])
    frame["position"] = frame["position"].astype(str).str.strip().str.upper()
    frame["date_of_birth"] = frame["date_of_birth_age"].map(_extract_birth_date)
    frame["age"] = frame["date_of_birth_age"].map(_extract_age)
    frame = frame[
        frame["position"].isin({"GK", "DF", "MF", "FW"})
        & frame["player_name"].notna()
        & frame["date_of_birth"].notna()
        & frame["age"].notna()
    ].copy()
    frame["caps"] = pd.to_numeric(frame["caps"], errors="coerce").fillna(0).astype(int)
    frame["goals"] = pd.to_numeric(frame["goals"], errors="coerce").fillna(0).astype(int)
    frame["shirt_number"] = pd.to_numeric(frame["shirt_number"], errors="coerce").astype("Int64")
    frame["source_team_name"] = team_name
    frame["source_player_count"] = len(frame)
    frame["squad_status"] = frame["source_player_count"].map(
        lambda count: "final_or_near_final" if count <= 26 else "preliminary_or_reduced"
    )
    frame["source_url"] = SQUADS_URL
    frame["downloaded_at_utc"] = downloaded_at_utc

    return frame[
        [
            "source_team_name",
            "squad_status",
            "source_player_count",
            "shirt_number",
            "position",
            "player_name",
            "is_captain",
            "date_of_birth",
            "age",
            "caps",
            "goals",
            "club",
            "source_url",
            "downloaded_at_utc",
        ]
    ]


def _find_section_table(heading: Tag) -> Tag | None:
    section_heading = heading.parent if isinstance(heading.parent, Tag) else heading

    for sibling in section_heading.find_next_siblings():
        if (
            sibling.name == "div"
            and "mw-heading" in sibling.get("class", [])
            and (
                "mw-heading2" in sibling.get("class", [])
                or "mw-heading3" in sibling.get("class", [])
            )
        ):
            return None

        if sibling.name == "table" and "wikitable" in sibling.get("class", []):
            return sibling

    return None


def fetch_squad_tables() -> pd.DataFrame:
    response = requests.get(SQUADS_URL, timeout=30, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()

    downloaded_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    soup = BeautifulSoup(response.text, "lxml")
    frames = []

    for heading in soup.select("h3"):
        team_name = heading.get_text(" ", strip=True).replace("[edit]", "").strip()
        table = _find_section_table(heading)
        if not team_name or table is None:
            continue

        parsed_tables = pd.read_html(StringIO(str(table)))
        if not parsed_tables:
            continue

        parsed = parsed_tables[0]
        if REQUIRED_COLUMNS.issubset(set(str(column).strip() for column in parsed.columns)):
            frames.append(_normalise_table(parsed, team_name, downloaded_at_utc))

    if not frames:
        raise ValueError("No squad tables were found.")

    return pd.concat(frames, ignore_index=True)


def main() -> None:
    squads = fetch_squad_tables()
    EXTERNAL_RAW_DIR.mkdir(parents=True, exist_ok=True)
    squads.to_csv(WORLD_CUP_SQUADS_PATH, index=False)

    team_count = squads["source_team_name"].nunique()
    player_count = len(squads)
    print(f"Wrote {player_count:,} players across {team_count:,} teams to {WORLD_CUP_SQUADS_PATH}")


if __name__ == "__main__":
    main()
