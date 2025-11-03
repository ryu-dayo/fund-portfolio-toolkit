import shutil
from pathlib import Path
from config_loader import load_config

TRANSACTION_SOURCE_FILE = Path("./data/transactions.csv")

def ensure_export_directory(path: str) -> Path:
    path = Path(path)
    if not path.exists():
        print(f"📁 Directory does not exist, creating: {path}")
        path.mkdir(parents=True, exist_ok=True)
    return path

def perform_backup(source: Path, target: Path) -> None:
    if not source.exists() or source.stat().st_size == 0:
        print("⚠️ Source file missing or empty, protecting backup and aborting export.")
        return
    
    if target.exists() and source.stat().st_size < (target.stat().st_size * 0.8):
        print("⚠️ Source file significantly smaller than backup, possible corruption, aborting export.")
        return

    shutil.copy2(source, target)
    print(f"✅ Transaction data backed up to {target}")

def transaction_backup(export_path: str) -> None:
    if not export_path:
        print("ℹ️ No backup directory configured; skipping transaction data backup")
        return

    target_path = ensure_export_directory(export_path)
    backup_path = target_path / f"{TRANSACTION_SOURCE_FILE.stem}_backup.csv"

    perform_backup(TRANSACTION_SOURCE_FILE, backup_path)

if __name__ == "__main__":
    cfg = load_config()
    export_path = cfg.get("export", {}).get("path")

    transaction_backup(export_path)