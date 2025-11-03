import reporting
import portfolio_data
from portfolio_snapshot import build_portfolio_snapshot
from config_loader import load_config
from transaction_backup import transaction_backup

def run_portfolio_snapshot(tracking_keys: list) -> None:

    analysis_df = build_portfolio_snapshot()

    # Render overall portfolio totals
    reporting.render_summary_totals(analysis_df)

    # Render detailed breakdowns
    if not isinstance(tracking_keys, list) or not tracking_keys:
        return

    needs_merge = any(key != "parent_strategy" for key in tracking_keys)
    merged_df = None
    if needs_merge:
        placeholder_df = portfolio_data.load_placeholder_positions()
        merged_df = portfolio_data.merge_positions(analysis_df, placeholder_df)
    
    unique_keys = list(dict.fromkeys(tracking_keys))
    for type_key in unique_keys:
        base_df = analysis_df if type_key == "parent_strategy" else merged_df
        breakdown = portfolio_data.aggregate_market_value_by_type(base_df, type_key)
        reporting.render_amount_breakdown(breakdown)

if __name__ == '__main__':
    config = load_config()
    tracking_keys = config.get("reporting", {}).get("tracking_type", [])
    export_path = config.get("export", {}).get("path")

    run_portfolio_snapshot(tracking_keys)
    transaction_backup(export_path)

