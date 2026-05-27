from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
EXTERNAL_RAW_DIR = RAW_DIR / "external"
PROCESSED_DIR = DATA_DIR / "processed"

GROUP_FIXTURES_PATH = RAW_DIR / "group_fixtures.csv"
KNOCKOUT_SLOTS_PATH = RAW_DIR / "knockout_slots.csv"
INTERNATIONAL_RESULTS_PATH = EXTERNAL_RAW_DIR / "results.csv"
SHOOTOUTS_PATH = EXTERNAL_RAW_DIR / "shootouts.csv"
BASELINE_PREDICTIONS_PATH = PROCESSED_DIR / "baseline_predictions.csv"
GROUP_PREDICTIONS_PATH = PROCESSED_DIR / "group_predictions_baseline.csv"
KNOCKOUT_PREDICTIONS_PATH = PROCESSED_DIR / "knockout_predictions_baseline.csv"
MODEL_GROUP_PREDICTIONS_V1_PATH = PROCESSED_DIR / "model_group_predictions_v1.csv"
MODEL_METRICS_V1_PATH = PROCESSED_DIR / "model_metrics_v1.json"
DUCKDB_PATH = PROCESSED_DIR / "world_cup.duckdb"
