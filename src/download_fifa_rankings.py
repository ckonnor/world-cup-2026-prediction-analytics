from __future__ import annotations

from datetime import UTC, datetime
import html
import json
import re
from io import StringIO

import pandas as pd
import requests

from world_cup.paths import EXTERNAL_RAW_DIR, FIFA_RANKINGS_PATH


DATO_HISTORICAL_RANKINGS_URL = (
    "https://raw.githubusercontent.com/Dato-Futbol/fifa-ranking/master/"
    "ranking_fifa_historical.csv"
)
FIFA_RANKING_PAGE_URL = "https://inside.fifa.com/fifa-world-ranking/men"
FIFA_RANKING_OVERVIEW_API_URL = "https://inside.fifa.com/api/ranking-overview"
FIFA_CURRENT_RANKING_API_URL = (
    "https://api.fifa.com/api/v3/rankings?gender=1&count=250&language=en"
)

TEAM_NAME_ALIASES = {
    "bosnia-herzegovina": "Bosnia and Herzegovina",
    "bosnia and herzegovina": "Bosnia and Herzegovina",
    "cabo verde": "Cape Verde",
    "cape verde islands": "Cape Verde",
    "congo dr": "DR Congo",
    "cote d'ivoire": "Ivory Coast",
    "cote divoire": "Ivory Coast",
    "côte d'ivoire": "Ivory Coast",
    "czechia": "Czech Republic",
    "ir iran": "Iran",
    "korea republic": "South Korea",
    "turkiye": "Turkey",
    "türkiye": "Turkey",
    "usa": "United States",
}


def _normalise_text(value: object) -> str:
    return " ".join(str(value).casefold().strip().split())


def _canonical_team_name(value: object) -> str:
    raw_name = str(value).strip()
    return TEAM_NAME_ALIASES.get(_normalise_text(raw_name), raw_name)


def _get_json(url: str, params: dict[str, object] | None = None) -> dict[str, object]:
    response = requests.get(
        url,
        params=params,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _download_historical_rankings(downloaded_at_utc: str) -> pd.DataFrame:
    response = requests.get(
        DATO_HISTORICAL_RANKINGS_URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    response.raise_for_status()
    raw = pd.read_csv(StringIO(response.text))
    raw["ranking_date"] = pd.to_datetime(raw["date"]).dt.date.astype("string")
    raw["rank"] = raw.groupby("ranking_date")["total_points"].rank(
        method="first",
        ascending=False,
        na_option="bottom",
    )
    raw.loc[raw["total_points"].isna(), "rank"] = pd.NA

    return pd.DataFrame(
        {
            "ranking_date": raw["ranking_date"],
            "team_name": raw["team"].map(_canonical_team_name),
            "country_code": raw["team_short"].astype("string").str.upper(),
            "rank": raw["rank"].astype("Int64"),
            "total_points": pd.to_numeric(raw["total_points"], errors="coerce"),
            "previous_rank": pd.NA,
            "previous_points": pd.NA,
            "confederation": pd.NA,
            "source_system": "dato_futbol_historical_csv",
            "source_url": DATO_HISTORICAL_RANKINGS_URL,
            "downloaded_at_utc": downloaded_at_utc,
        }
    )


def _extract_available_dates() -> list[dict[str, str]]:
    response = requests.get(
        FIFA_RANKING_PAGE_URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    response.raise_for_status()
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        response.text,
    )
    if not match:
        return []

    data = json.loads(html.unescape(match.group(1)))
    ranking = data["props"]["pageProps"]["pageData"]["ranking"]
    return ranking.get("allAvailableDates", [])


def _download_official_window_rankings(downloaded_at_utc: str) -> pd.DataFrame:
    rows = []
    for ranking_date in _extract_available_dates():
        date_id = ranking_date["id"]
        ranking_date_value = ranking_date["matchWindowEndDate"]
        if ranking_date_value < "2024-09-19" or date_id.startswith("FRS_"):
            continue

        payload = _get_json(
            FIFA_RANKING_OVERVIEW_API_URL,
            params={
                "locale": "en",
                "dateId": date_id,
                "rankingType": "football",
            },
        )
        for item in payload.get("rankings", []):
            ranking_item = item["rankingItem"]
            rows.append(
                {
                    "ranking_date": ranking_date_value,
                    "team_name": _canonical_team_name(ranking_item["name"]),
                    "country_code": str(ranking_item["countryCode"]).upper(),
                    "rank": ranking_item.get("rank"),
                    "total_points": ranking_item.get("totalPoints"),
                    "previous_rank": ranking_item.get("previousRank"),
                    "previous_points": item.get("previousPoints"),
                    "confederation": (item.get("tag") or {}).get("id"),
                    "source_system": "fifa_ranking_overview_api",
                    "source_url": FIFA_RANKING_OVERVIEW_API_URL,
                    "downloaded_at_utc": downloaded_at_utc,
                }
            )

    return pd.DataFrame(rows)


def _team_description(team_names: list[dict[str, str]]) -> str:
    for team_name in team_names:
        if team_name.get("Locale") == "en-GB":
            return str(team_name.get("Description", ""))
    return str(team_names[0].get("Description", "")) if team_names else ""


def _download_current_official_rankings(downloaded_at_utc: str) -> pd.DataFrame:
    payload = _get_json(FIFA_CURRENT_RANKING_API_URL)
    rows = []
    for item in payload.get("Results", []):
        pub_date = pd.to_datetime(item["PubDate"]).date().isoformat()
        rows.append(
            {
                "ranking_date": pub_date,
                "team_name": _canonical_team_name(_team_description(item["TeamName"])),
                "country_code": str(item["IdCountry"]).upper(),
                "rank": item.get("Rank"),
                "total_points": item.get("DecimalTotalPoints"),
                "previous_rank": item.get("PrevRank"),
                "previous_points": item.get("DecimalPrevPoints"),
                "confederation": item.get("ConfederationName"),
                "source_system": "fifa_current_rankings_api",
                "source_url": FIFA_CURRENT_RANKING_API_URL,
                "downloaded_at_utc": downloaded_at_utc,
            }
        )
    return pd.DataFrame(rows)


def download_fifa_rankings() -> pd.DataFrame:
    downloaded_at_utc = datetime.now(UTC).replace(microsecond=0).isoformat()
    frames = [
        _download_historical_rankings(downloaded_at_utc),
        _download_official_window_rankings(downloaded_at_utc),
        _download_current_official_rankings(downloaded_at_utc),
    ]
    non_empty_frames = [
        frame.dropna(axis=1, how="all")
        for frame in frames
        if not frame.empty
    ]
    combined = pd.concat(non_empty_frames, ignore_index=True)
    combined["ranking_date"] = pd.to_datetime(combined["ranking_date"]).dt.date.astype("string")
    combined["rank"] = pd.to_numeric(combined["rank"], errors="coerce").astype("Int64")
    combined["total_points"] = pd.to_numeric(combined["total_points"], errors="coerce")
    combined["source_priority"] = combined["source_system"].map(
        {
            "fifa_current_rankings_api": 3,
            "fifa_ranking_overview_api": 2,
            "dato_futbol_historical_csv": 1,
        }
    )
    combined = (
        combined.sort_values(["ranking_date", "country_code", "source_priority"])
        .drop_duplicates(["ranking_date", "country_code"], keep="last")
        .drop(columns="source_priority")
        .sort_values(["ranking_date", "rank", "team_name"])
    )
    combined.to_csv(FIFA_RANKINGS_PATH, index=False)
    return combined


def main() -> None:
    EXTERNAL_RAW_DIR.mkdir(parents=True, exist_ok=True)
    print("Downloading FIFA ranking history and current ranking snapshot...")
    rankings = download_fifa_rankings()
    print(
        f"- wrote {len(rankings):,} rows across "
        f"{rankings['ranking_date'].nunique():,} ranking dates to {FIFA_RANKINGS_PATH}"
    )


if __name__ == "__main__":
    main()
