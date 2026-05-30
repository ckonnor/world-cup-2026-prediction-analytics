from __future__ import annotations

import csv
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DATA_DIR = PROJECT_ROOT / "app" / "data"
TEAM_PROFILE_PATH = APP_DATA_DIR / "dashboard_team_profiles.csv"
OUTPUT_PATH = APP_DATA_DIR / "dashboard_polymarket_outrights.csv"
POLYMARKET_EVENT_URL = "https://gamma-api.polymarket.com/events/slug/world-cup-winner"
POLYMARKET_EVENT_PAGE = "https://polymarket.com/event/2026-fifa-world-cup-winner-595"

TEAM_NAME_OVERRIDES = {
    "Bosnia and Herzegovina": "Bosnia-Herzegovina",
    "Cabo Verde": "Cape Verde",
    "Côte d'Ivoire": "Ivory Coast",
}


def _fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object from {url}")
    return payload


def _yes_probability(market: dict[str, Any]) -> float | None:
    prices_raw = market.get("outcomePrices")
    if not prices_raw:
        return None
    prices = json.loads(prices_raw)
    if not prices:
        return None
    return float(prices[0])


def _team_names() -> list[str]:
    with TEAM_PROFILE_PATH.open(newline="", encoding="utf-8") as file:
        return [row["team_name"] for row in csv.DictReader(file)]


def fetch_polymarket_outrights() -> list[dict[str, Any]]:
    event = _fetch_json(POLYMARKET_EVENT_URL)
    markets_by_title = {
        market["groupItemTitle"]: market
        for market in event.get("markets", [])
        if market.get("groupItemTitle")
    }
    snapshot_at = event.get("updatedAt") or datetime.now(timezone.utc).isoformat()

    rows = []
    missing_teams = []
    for team_name in _team_names():
        market_name = TEAM_NAME_OVERRIDES.get(team_name, team_name)
        market = markets_by_title.get(market_name)
        if market is None:
            missing_teams.append(team_name)
            probability = None
            best_bid = None
            best_ask = None
            last_trade_price = None
            market_slug = None
        else:
            probability = _yes_probability(market)
            best_bid = market.get("bestBid")
            best_ask = market.get("bestAsk")
            last_trade_price = market.get("lastTradePrice")
            market_slug = market.get("slug")

        rows.append(
            {
                "team_name": team_name,
                "polymarket_market_name": market_name,
                "polymarket_outright_probability": probability,
                "polymarket_best_bid": best_bid,
                "polymarket_best_ask": best_ask,
                "polymarket_last_trade_price": last_trade_price,
                "polymarket_market_slug": market_slug,
                "polymarket_event_url": POLYMARKET_EVENT_PAGE,
                "polymarket_snapshot_at": snapshot_at,
            }
        )

    if missing_teams:
        missing_text = ", ".join(sorted(missing_teams))
        raise ValueError(f"Missing Polymarket outright markets for: {missing_text}")
    return rows


def write_polymarket_outrights() -> Path:
    rows = fetch_polymarket_outrights()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return OUTPUT_PATH


def main() -> None:
    output_path = write_polymarket_outrights()
    print(f"Wrote Polymarket outright snapshot: {output_path}")


if __name__ == "__main__":
    main()
