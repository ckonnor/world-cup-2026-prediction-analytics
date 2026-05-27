from __future__ import annotations

from world_cup.baseline import build_baseline_predictions
from world_cup.io import check_required_raw_files, load_group_fixtures, load_knockout_slots
from world_cup.paths import BASELINE_PREDICTIONS_PATH, PROCESSED_DIR


def main() -> None:
    missing = check_required_raw_files()
    if missing:
        print("Missing required raw files:")
        for path in missing:
            print(f"- {path}")
        raise SystemExit(1)

    predictions = build_baseline_predictions(
        group_fixtures=load_group_fixtures(),
        knockout_slots=load_knockout_slots(),
    )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(BASELINE_PREDICTIONS_PATH, index=False)
    print(f"Wrote {len(predictions):,} predictions to {BASELINE_PREDICTIONS_PATH}")


if __name__ == "__main__":
    main()
