from __future__ import annotations

from train_model import outcome_from_scores


def test_outcome_from_scores() -> None:
    assert outcome_from_scores(2, 1) == "home"
    assert outcome_from_scores(1, 2) == "away"
    assert outcome_from_scores(1, 1) == "draw"
