import pandas as pd
import numpy as np

from transaction_analysis import run_trans_analysis
from fund_data_providers import get_fund_data

def build_portfolio_snapshot() -> pd.DataFrame:
    
    snapshot = run_trans_analysis()
    nav_lookup = fetch_nav_lookup(snapshot)
    return enrich_portfolio_metrics(snapshot, nav_lookup)

def fetch_nav_lookup(frame: pd.DataFrame) -> dict[str, dict[str, str]]:
    
    active_codes = frame.loc[frame["holding_units"] > 0, "fund_code"].dropna().unique()
    if active_codes.size == 0:
        return {}
    
    return get_fund_data(active_codes)

def enrich_portfolio_metrics(frame: pd.DataFrame, nav_lookup: dict[str, dict[str, str]]) -> pd.DataFrame:
    
    if nav_lookup:
        # Expand fund metadata (name, nav, etc.) from lookup
        nav_records = frame["fund_code"].map(lambda code: nav_lookup.get(code, {}))
        nav_df = pd.DataFrame.from_records(nav_records.tolist())
    else:
        nav_df = pd.DataFrame(index=frame.index)
    frame["fund_name"] = nav_df.get("fund_name", "").fillna("")
    frame["nav_per_unit"] = pd.to_numeric(nav_df.get("nav_per_unit", 0), errors="coerce").fillna(0)

    current_value = frame["nav_per_unit"] * frame["holding_units"]
    frame["market_value"] = current_value.round(2)
    frame["cumulative_pnl"] = (
        current_value + frame["cumulative_cash_dividend"] + frame["net_trade_cashflow"]
    ).round(2)

    # Calculate valuation and performance metrics
    has_position = frame["holding_units"] > 0
    unrealized_pnl_calc = current_value - frame["total_investment_cost"]  + frame["cash_dividend"]

    frame["unrealized_pnl"] = np.where(has_position, unrealized_pnl_calc.round(2), 0)
    has_cost = frame["total_investment_cost"] > 0   # Prevent division errors when cost is zero (e.g., gifted shares)
    frame["holding_return_pct"] = np.where(has_position & has_cost, (unrealized_pnl_calc / frame["total_investment_cost"]).round(4), 0)

    frame["average_cost_per_unit"] = np.where(has_position, (frame["total_investment_cost"] / frame["holding_units"]).round(4), 0)

    return frame

