from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

GROUP_FIXTURES_PATH = RAW_DIR / "group_fixtures.csv"
KNOCKOUT_SLOTS_PATH = RAW_DIR / "knockout_slots.csv"
BASELINE_PREDICTIONS_PATH = PROCESSED_DIR / "baseline_predictions.csv"
