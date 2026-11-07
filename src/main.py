#!/usr/bin/env python3
import reporting
from config_loader import AppConfig, load_config
from portfolio_snapshot import (
    aggregate_market_value_by_type,
    build_portfolio_snapshot,
    load_placeholder_positions,
    merge_positions,
)
from pricing_providers import PricingProvider


def run_portfolio_snapshot(
    config: AppConfig,
    provider: PricingProvider | None = None,
) -> None:
    analysis_df = build_portfolio_snapshot(config, provider)

    missing_prices = analysis_df.loc[
        (analysis_df["holding_units"] > 0) & analysis_df["price_per_unit"].isna(),
        "fund_code",
    ].unique()
    if missing_prices.size:
        reporting.render_missing_prices(missing_prices)
        return

    reporting.render_valuation_totals(analysis_df)

    # Render detailed breakdowns
    if not config.tracking_keys:
        return

    needs_merge = any(key != "parent_strategy" for key in config.tracking_keys)
    merged_df = None
    if needs_merge:
        placeholder_df = load_placeholder_positions(config.placeholders)
        merged_df = merge_positions(analysis_df, placeholder_df)

    unique_keys = list(dict.fromkeys(config.tracking_keys))
    for type_key in unique_keys:
        base_df = analysis_df if type_key == "parent_strategy" else merged_df
        breakdown = aggregate_market_value_by_type(base_df, type_key)
        reporting.render_amount_breakdown(breakdown)


def main() -> None:
    config = load_config()
    run_portfolio_snapshot(config)


if __name__ == "__main__":
    main()
