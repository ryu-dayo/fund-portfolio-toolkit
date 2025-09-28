import reporting
import portfolio_data
from portfolio_snapshot import build_portfolio_snapshot
from config_loader import load_config

def run_portfolio_snapshot() -> None:

    analysis_df = build_portfolio_snapshot()

    # Render overall portfolio totals
    reporting.render_summary_totals(analysis_df)

    placeholder_df = portfolio_data.load_placeholder_positions()
    merged_df = portfolio_data.merge_positions(analysis_df, placeholder_df)

    config = load_config()
    tracking_keys = config.get("reporting", {}).get("tracking_type", [])

    # Render detailed breakdowns
    if not isinstance(tracking_keys, list) or not tracking_keys:
        return
    
    for type_key in tracking_keys:
        base_df = analysis_df if type_key == "parent_strategy" else merged_df
        breakdown = portfolio_data.aggregate_market_value_by_type(base_df, type_key)
        reporting.render_amount_breakdown(breakdown)

if __name__ == '__main__':
    run_portfolio_snapshot()
