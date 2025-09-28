import pandas as pd

_DEFAULT_SEPARATOR = "-" * 30

def render_label_value_pairs(
    pairs: list[tuple[str, float]],
    label_width: int = 15,
    value_width: int = 12,
    separator: str = _DEFAULT_SEPARATOR,
) -> None:
    
    for label, value in pairs:
        print(f"{label:<{label_width}}{value:>{value_width}.2f}")
    print(separator)


def render_summary_totals(
    frame: pd.DataFrame,
    metrics: dict[str, str] | None = None,
    separator: str = _DEFAULT_SEPARATOR,
) -> None:
    
    default_metrics = {
        "Total Value": "market_value",
        "Unrealized P&L": "unrealized_pnl",
        "Cumulative P&L": "cumulative_pnl",
    }
    metrics = metrics or default_metrics

    totals: list[tuple[str, float]] = []
    for label, column in metrics.items():
        if column not in frame:
            continue
        totals.append((label, frame[column].sum().round(2)))

    render_label_value_pairs(totals, separator=separator)


def render_amount_breakdown(
    frame: pd.DataFrame,
    amount_column: str = "market_value",
    percentage_label: str = "percentage",
    separator: str = _DEFAULT_SEPARATOR,
) -> None:
    
    if frame.empty:
        print("No rows available for breakdown.")
        print(separator)
        return

    if amount_column not in frame:
        raise KeyError(f"Column {amount_column!r} is missing from the DataFrame.")

    total_amount = frame[amount_column].sum()
    if total_amount == 0:
        print("Total amount is zero; percentage breakdown is undefined.")
        print(separator)
        return

    breakdown = frame.copy()
    breakdown[percentage_label] = breakdown[amount_column] / total_amount
    print(breakdown.to_string(
        index=False,
        header=False,
        formatters={percentage_label: lambda v: f"{v:.2%}"}
    ))
    print(separator)
