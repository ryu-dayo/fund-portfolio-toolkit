from pathlib import Path
from typing import Protocol, cast

import pandas as pd

from app_paths import TRANSACTION_PATH


class _TransactionRow(Protocol):
    transaction_type: str
    confirmed_amount: float
    fee: float
    confirmed_units: float


class FundPosition:
    """Track position cost, share count, and cash movements for a single fund."""

    def __init__(self):
        self.total_cost = 0.0
        self.total_shares = 0.0
        self.total_cash_dividends = 0.0
        self.holding_cash_dividends = 0.0
        self.net_trade_cash = 0.0

    def buy(self, cash, shares):
        self.total_cost += cash
        self.total_shares += shares
        self.net_trade_cash -= cash

    def sell(self, cash, shares):
        shares_to_sell = shares
        if shares_to_sell > round(self.total_shares, 2):
            raise ValueError("Sell quantity exceeds current share balance")

        sell_ratio = shares_to_sell / self.total_shares
        cost_to_deduct = sell_ratio * self.total_cost
        self.total_cost -= cost_to_deduct
        self.total_shares -= shares_to_sell
        self.holding_cash_dividends -= sell_ratio * self.holding_cash_dividends
        self.net_trade_cash += cash

        if self.total_shares == 0:
            self.holding_cash_dividends = 0

    def income(self, cash=0, shares=0):
        if cash and cash > 0:
            self.total_cash_dividends += cash
            self.holding_cash_dividends += cash
        if shares and shares > 0:
            self.total_shares += shares

    def average_cost_per_unit(self):
        if self.total_shares == 0:
            return 0.0
        return self.total_cost / self.total_shares

    def status(self):
        print(
            f"Total cost: {self.total_cost: .2f}, total shares: {self.total_shares: .2f}"
        )
        print(f"Average cost per unit: {self.average_cost_per_unit(): .4f}")


# Increment this when transaction calculation semantics or summary schema changes.
TRANSACTION_ANALYSIS_VERSION = 1
TRANSACTION_SUMMARY_COLUMNS = [
    "fund_code",
    "total_investment_cost",
    "holding_units",
    "average_cost_per_unit",
    "parent_strategy",
    "child_strategy",
    "cash_dividend",
    "cumulative_cash_dividend",
    "net_trade_cashflow",
]


def read_transactions(source_path: Path) -> pd.DataFrame:
    return pd.read_csv(source_path, dtype={"fund_code": str})


def analyze_transactions(transactions: pd.DataFrame) -> pd.DataFrame:
    ordered = transactions.sort_values(by="trade_date").reset_index(drop=True)
    grouped = ordered.groupby(["fund_code", "parent_strategy"])

    rows = []
    for (fund_code, parent), frame in grouped:
        position = FundPosition()

        for raw_row in frame.itertuples():
            row = cast(_TransactionRow, raw_row)
            match row.transaction_type:
                case "Buy":
                    position.buy(row.confirmed_amount + row.fee, row.confirmed_units)
                case "Sell":
                    position.sell(row.confirmed_amount, row.confirmed_units)
                case "Income":
                    position.income(row.confirmed_amount, row.confirmed_units)

        child_strategies = frame["child_strategy"].dropna().unique()
        child_strategy = child_strategies[0] if child_strategies.size else ""
        rows.append(
            [
                fund_code,
                position.total_cost,
                round(position.total_shares, 2),
                round(position.average_cost_per_unit(), 4),
                parent,
                child_strategy,
                position.holding_cash_dividends,
                position.total_cash_dividends,
                position.net_trade_cash,
            ]
        )

    return pd.DataFrame(rows, columns=TRANSACTION_SUMMARY_COLUMNS)


def run_trans_analysis(
    source_path: Path = TRANSACTION_PATH,
) -> pd.DataFrame:
    """Compatibility wrapper for callers that do not use the cache layer."""
    return analyze_transactions(read_transactions(source_path))
