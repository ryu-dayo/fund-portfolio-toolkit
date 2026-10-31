import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app_paths import CONFIG_PATH


@dataclass(frozen=True)
class AppConfig:
    tracking_keys: tuple[str, ...]
    placeholders: tuple[dict[str, Any] | list[Any], ...]
    pricing_provider_name: str | None
    export_path: Path | None


def _resolve_path(value: str, project_root: Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else project_root / path


def load_config(config_path: Path = CONFIG_PATH) -> AppConfig:
    config_path = config_path.resolve()
    try:
        with config_path.open(encoding="utf-8") as stream:
            payload = json.load(stream)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Unable to locate config at {config_path}.") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in config {config_path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise TypeError("Config root must be a JSON object.")

    config_root = config_path.parent.parent
    reporting = payload.get("reporting", {})
    pricing = payload.get("pricing", {})
    export = payload.get("export", {})

    tracking_keys = reporting.get("tracking_type", []) or []
    placeholders = reporting.get("placeholder", []) or []
    if not isinstance(tracking_keys, list) or not all(
        isinstance(key, str) for key in tracking_keys
    ):
        raise ValueError("reporting.tracking_type must be a list of strings.")
    if not isinstance(placeholders, list) or not all(
        isinstance(item, (dict, list)) for item in placeholders
    ):
        raise ValueError("reporting.placeholder must contain objects or row lists.")

    export_value = export.get("path")
    export_path = _resolve_path(export_value, config_root) if export_value else None
    pricing_provider_name = pricing.get("provider") or None
    if pricing_provider_name is not None and not isinstance(pricing_provider_name, str):
        raise ValueError("pricing.provider must be a string.")

    return AppConfig(
        tracking_keys=tuple(tracking_keys),
        placeholders=tuple(placeholders),
        pricing_provider_name=pricing_provider_name,
        export_path=export_path,
    )
