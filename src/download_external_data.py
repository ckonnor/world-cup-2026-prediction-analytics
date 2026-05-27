from __future__ import annotations

from dataclasses import dataclass
from urllib.request import urlretrieve

import pandas as pd

from world_cup.paths import EXTERNAL_RAW_DIR, INTERNATIONAL_RESULTS_PATH, SHOOTOUTS_PATH


@dataclass(frozen=True)
class ExternalCsv:
    name: str
    url: str
    path: object


EXTERNAL_CSVS = [
    ExternalCsv(
        name="international_results",
        url="https://raw.githubusercontent.com/martj42/international_results/master/results.csv",
        path=INTERNATIONAL_RESULTS_PATH,
    ),
    ExternalCsv(
        name="shootouts",
        url="https://raw.githubusercontent.com/martj42/international_results/master/shootouts.csv",
        path=SHOOTOUTS_PATH,
    ),
]


def main() -> None:
    EXTERNAL_RAW_DIR.mkdir(parents=True, exist_ok=True)

    for source in EXTERNAL_CSVS:
        print(f"Downloading {source.name}...")
        urlretrieve(source.url, source.path)
        row_count = len(pd.read_csv(source.path))
        print(f"- wrote {row_count:,} rows to {source.path}")


if __name__ == "__main__":
    main()
