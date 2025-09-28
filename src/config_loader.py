import json
from pathlib import Path

def load_config(config_path: Path = Path("./data/config.json")) -> dict:
    try:
        with config_path.open(encoding="utf-8") as stream:
            return json.load(stream)
    except FileNotFoundError:
        raise FileNotFoundError(f"Unable to locate placeholder config at {config_path}.")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in placeholder config {config_path}: {exc}") from exc