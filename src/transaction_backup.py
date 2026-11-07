import shutil
import tempfile
from pathlib import Path

from app_paths import TRANSACTION_PATH
from file_fingerprint import calculate_file_fingerprint


def ensure_export_directory(path: Path) -> Path:
    if not path.exists():
        print(f"📁 Directory does not exist, creating: {path}")
        path.mkdir(parents=True, exist_ok=True)
    return path


def perform_backup(
    source: Path,
    target: Path,
    *,
    source_fingerprint: str | None = None,
) -> None:
    if not source.exists() or source.stat().st_size == 0:
        print("⚠️ Source file missing or empty, protecting backup and aborting export.")
        return

    if source_fingerprint is None:
        source_fingerprint = calculate_file_fingerprint(source)

    try:
        target_fingerprint = calculate_file_fingerprint(target)
    except FileNotFoundError:
        target_fingerprint = None

    if target_fingerprint == source_fingerprint:
        return

    if target.exists() and source.stat().st_size < (target.stat().st_size * 0.8):
        print(
            "⚠️ Source file significantly smaller than backup, possible corruption, aborting export."
        )
        return

    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
        temporary_path = Path(stream.name)

    try:
        shutil.copy2(source, temporary_path)

        if calculate_file_fingerprint(temporary_path) != source_fingerprint:
            print("⚠️ Backup content differs from expected source; skipping replacement.")
            return

        temporary_path.replace(target)
    finally:
        temporary_path.unlink(missing_ok=True)

    print(f"✅ Transaction data backed up to {target}")


def transaction_backup(
    export_path: Path | None,
    source_path: Path = TRANSACTION_PATH,
    *,
    source_fingerprint: str | None = None,
) -> None:
    if not export_path:
        print("ℹ️ No backup directory configured; skipping transaction data backup")
        return

    target_path = ensure_export_directory(export_path)
    backup_path = target_path / f"{source_path.stem}_backup.csv"

    perform_backup(source_path, backup_path, source_fingerprint=source_fingerprint)


if __name__ == "__main__":
    from config_loader import load_config

    config = load_config()
    transaction_backup(config.export_path)
