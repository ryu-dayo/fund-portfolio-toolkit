import json
import os
import tempfile
from pathlib import Path

import pandas as pd

from file_fingerprint import calculate_file_fingerprint
from transaction_analysis import (
    TRANSACTION_ANALYSIS_VERSION,
    TRANSACTION_SUMMARY_COLUMNS,
    analyze_transactions,
    read_transactions,
)


def _read_cache(cache_path: Path, source_fingerprint: str) -> pd.DataFrame | None:
    try:
        with cache_path.open(encoding="utf-8") as stream:
            payload = json.load(stream)
    except (
        FileNotFoundError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return None

    if not isinstance(payload, dict):
        return None
    if payload.get("analysis_version") != TRANSACTION_ANALYSIS_VERSION:
        return None
    if payload.get("source_sha256") != source_fingerprint:
        return None

    records = payload.get("summary")
    if not isinstance(records, list) or not all(
        isinstance(row, dict) for row in records
    ):
        return None
    return pd.DataFrame.from_records(records, columns=TRANSACTION_SUMMARY_COLUMNS)


def _write_cache(
    cache_path: Path,
    source_fingerprint: str,
    transaction_count: int,
    summary: pd.DataFrame,
) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "analysis_version": TRANSACTION_ANALYSIS_VERSION,
        "source_sha256": source_fingerprint,
        "transaction_count": transaction_count,
        "summary": summary.to_dict(orient="records"),
    }

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=cache_path.parent,
            prefix=f".{cache_path.name}.",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, allow_nan=False, indent=2)
            stream.write("\n")
        os.replace(temporary_path, cache_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def load_transaction_summary(
    source_path: Path,
    cache_path: Path,
    *,
    source_fingerprint: str | None = None,
) -> pd.DataFrame:
    if source_fingerprint is None:
        source_fingerprint = calculate_file_fingerprint(source_path)

    cached = _read_cache(cache_path, source_fingerprint)
    if cached is not None:
        return cached.copy()

    transactions = read_transactions(source_path)
    summary = analyze_transactions(transactions)
    _write_cache(cache_path, source_fingerprint, len(transactions), summary)
    return summary
