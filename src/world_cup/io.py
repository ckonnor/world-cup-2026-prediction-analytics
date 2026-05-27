from __future__ import annotations

import pandas as pd

from world_cup.paths import GROUP_FIXTURES_PATH, KNOCKOUT_SLOTS_PATH


REQUIRED_RAW_FILES = {
    "group_fixtures": GROUP_FIXTURES_PATH,
    "knockout_slots": KNOCKOUT_SLOTS_PATH,
}


def check_required_raw_files() -> list[str]:
    missing = [str(path) for path in REQUIRED_RAW_FILES.values() if not path.exists()]
    return missing


def load_group_fixtures() -> pd.DataFrame:
    return pd.read_csv(GROUP_FIXTURES_PATH)


def load_knockout_slots() -> pd.DataFrame:
    return pd.read_csv(KNOCKOUT_SLOTS_PATH)
