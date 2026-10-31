from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = PROJECT_ROOT / ".cache"

CONFIG_PATH = DATA_DIR / "config.json"
TRANSACTION_PATH = DATA_DIR / "transactions.csv"
TRANSACTION_CACHE_PATH = CACHE_DIR / "transaction-analysis.json"
