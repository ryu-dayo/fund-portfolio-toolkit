import pandas as pd
from fund_position import FundPosition

def run_trans_analysis() -> pd.DataFrame:
    csv = pd.read_csv("./data/transactions.csv", dtype={"fund_code": str})
    csv = csv.sort_values(by="trade_date").reset_index(drop=True)
    fund = csv.groupby(["fund_code", "parent_strategy"])

    rows = []
    for (fund_code, parent), df in fund:
        f = FundPosition()
        
        for row in df.itertuples():
            match row.transaction_type:
                case "Buy":
                    f.buy(row.confirmed_amount + row.fee, row.confirmed_units)
                case "Sell":
                    f.sell(row.confirmed_amount, row.confirmed_units)
                case "Income":
                    f.income(row.confirmed_amount, row.confirmed_units)

        child = df["child_strategy"].dropna().unique()
        child = child[0] if child.size else ""
        
        summary_row = [fund_code, f.total_cost, round(f.total_shares, 2), parent, child, f.holding_cash_dividends, f.total_cash_dividends, f.net_trade_cash]
        rows.append(summary_row)
    
    return pd.DataFrame(rows, columns=["fund_code", "total_investment_cost", "holding_units", "parent_strategy", "child_strategy", "cash_dividend", "cumulative_cash_dividend", "net_trade_cashflow"])
