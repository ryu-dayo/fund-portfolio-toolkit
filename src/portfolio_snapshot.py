from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from app_paths import TRANSACTION_CACHE_PATH, TRANSACTION_PATH
from config_loader import AppConfig
from file_fingerprint import calculate_file_fingerprint
from pricing_providers import FundPriceMap, PricingProvider, get_fund_prices
from transaction_backup import transaction_backup
from transaction_cache import load_transaction_summary

_PLACEHOLDER_COLUMNS = [
    "fund_code",
    "parent_strategy",
    "child_strategy",
    "market_value",
]


def load_placeholder_positions(
    positions: Sequence[Mapping[str, Any] | Sequence[Any]] | None = None,
) -> pd.DataFrame:
    if not positions:
        return pd.DataFrame(columns=_PLACEHOLDER_COLUMNS)
    return pd.DataFrame(positions, columns=_PLACEHOLDER_COLUMNS)


def merge_positions(origin: pd.DataFrame, placeholders: pd.DataFrame) -> pd.DataFrame:
    combined = pd.concat([origin, placeholders], ignore_index=True)
    combined["child_strategy"] = combined["child_strategy"].fillna(
        combined["fund_code"]
    )
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


def build_portfolio_positions(
    *,
    transaction_path: Path = TRANSACTION_PATH,
    transaction_cache_path: Path = TRANSACTION_CACHE_PATH,
    source_fingerprint: str | None = None,
) -> pd.DataFrame:
    return load_transaction_summary(
        transaction_path,
        transaction_cache_path,
        source_fingerprint=source_fingerprint
    )


def build_portfolio_snapshot(
    config: AppConfig,
    provider: PricingProvider | None = None,
    *,
    transaction_path: Path = TRANSACTION_PATH,
    transaction_cache_path: Path = TRANSACTION_CACHE_PATH,
) -> pd.DataFrame:
    source_fingerprint = calculate_file_fingerprint(transaction_path)
    positions = build_portfolio_positions(
        transaction_path=transaction_path,
        transaction_cache_path=transaction_cache_path,
        source_fingerprint=source_fingerprint,
    )

    if config.export_path is not None:
        try:
            transaction_backup(
                config.export_path,
                transaction_path,
                source_fingerprint=source_fingerprint,
            )
        except OSError as exc:
            print(f"⚠️ Failed to backup transaction data: {exc}")

    price_lookup = fetch_price_lookup(
        positions,
        config.pricing_provider_name,
        provider,
    )
    return enrich_portfolio_metrics(positions, price_lookup)


def fetch_price_lookup(
    frame: pd.DataFrame,
    provider_name: str | None,
    provider: PricingProvider | None = None,
) -> FundPriceMap:
    active_codes = frame.loc[frame["holding_units"] > 0, "fund_code"].dropna().unique()
    if active_codes.size == 0:
        return {}

    return get_fund_prices(active_codes, provider_name, provider)


def enrich_portfolio_metrics(
    frame: pd.DataFrame,
    price_lookup: FundPriceMap,
) -> pd.DataFrame:
    result = frame.copy()
    prices = result["fund_code"].map(lambda code: price_lookup.get(str(code)))

    result["fund_name"] = prices.map(
        lambda price: price.fund_name if price is not None else ""
    )
    result["price_per_unit"] = pd.Series(
        [
            price.price_per_unit if price is not None else float("nan")
            for price in prices
        ],
        index=result.index,
        dtype="float64",
    )
    result["price_type"] = prices.map(
        lambda price: price.price_type if price is not None else ""
    )
    result["price_as_of"] = prices.map(
        lambda price: price.as_of if price is not None else None
    )

    has_position = result["holding_units"] > 0
    current_value = result["price_per_unit"] * result["holding_units"]
    current_value = current_value.where(has_position, 0.0)
    result["market_value"] = current_value.round(2)
    result["cumulative_pnl"] = (
        current_value
        + result["cumulative_cash_dividend"]
        + result["net_trade_cashflow"]
    ).round(2)

    unrealized_pnl = (
        current_value - result["total_investment_cost"] + result["cash_dividend"]
    )
    result["unrealized_pnl"] = unrealized_pnl.where(has_position, 0.0).round(2)

    has_cost = result["total_investment_cost"] > 0
    result["holding_return_pct"] = (
        (unrealized_pnl / result["total_investment_cost"])
        .where(has_position & has_cost, 0.0)
        .round(4)
    )

    return result
