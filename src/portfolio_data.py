from config_loader import load_config

import pandas as pd

_PLACEHOLDER_COLUMNS: list[str] = ["fund_code", "parent_strategy", "child_strategy", "market_value"]

def load_placeholder_positions(config: dict | None = None) -> pd.DataFrame:

    config = config or load_config()
    positions = config.get("reporting", {}).get("placeholder", [])
    if not positions:
        return pd.DataFrame(columns=_PLACEHOLDER_COLUMNS)
    return pd.DataFrame(positions, columns=_PLACEHOLDER_COLUMNS)

def merge_positions(origin: pd.DataFrame, placeholders: pd.DataFrame) -> pd.DataFrame:

    combined = pd.concat([origin, placeholders], ignore_index=True)
    combined["child_strategy"] = combined["child_strategy"].fillna(combined["fund_code"]) # Default child strategy to fund code when missing
    return combined

def aggregate_market_value_by_type(
        frame: pd.DataFrame,
        type_key: str,
        value_column: str = "market_value",
) -> pd.DataFrame:
    
    if value_column not in frame:
        raise KeyError(f"Column {value_column!r} is missing from the frame.")

    if type_key == "parent_strategy":
        return frame.groupby(type_key, as_index=False)[value_column].sum()
    
    mask = frame["parent_strategy"].eq(type_key)
    if not mask.any():
        raise ValueError(f"Type Key {type_key!r} not found.")
    
    return frame.loc[mask].groupby("child_strategy", as_index=False)[value_column].sum()
    