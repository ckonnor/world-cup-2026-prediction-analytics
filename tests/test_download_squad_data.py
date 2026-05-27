from __future__ import annotations

import pandas as pd
from bs4 import BeautifulSoup

from download_squad_data import _find_section_table, _normalise_table


def test_find_section_table_does_not_cross_into_next_team() -> None:
    soup = BeautifulSoup(
        """
        <div class="mw-heading mw-heading3"><h3>Team A</h3></div>
        <p>Team A will announce their squad later.</p>
        <div class="mw-heading mw-heading3"><h3>Team B</h3></div>
        <table class="wikitable"><tr><th>Pos.</th></tr><tr><td>GK</td></tr></table>
        """,
        "html.parser",
    )

    team_a_heading, team_b_heading = soup.select("h3")

    assert _find_section_table(team_a_heading) is None
    assert _find_section_table(team_b_heading) is not None


def test_normalise_table_filters_empty_separator_rows() -> None:
    table = pd.DataFrame(
        [
            {
                "No.": 1,
                "Pos.": "GK",
                "Player": "Example Keeper",
                "Date of birth (age)": "January 1, 2000 (aged 26)",
                "Caps": 10,
                "Goals": 0,
                "Club": "Example FC",
            },
            {
                "No.": None,
                "Pos.": None,
                "Player": None,
                "Date of birth (age)": None,
                "Caps": None,
                "Goals": None,
                "Club": None,
            },
        ]
    )

    normalised = _normalise_table(table, "Example", "2026-05-27T00:00:00+00:00")

    assert len(normalised) == 1
    assert normalised.loc[0, "player_name"] == "Example Keeper"
    assert normalised.loc[0, "source_player_count"] == 1
