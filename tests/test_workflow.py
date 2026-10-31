import json

import pandas as pd

import transaction_cache
from app_paths import TRANSACTION_CACHE_PATH, TRANSACTION_PATH
from config_loader import AppConfig, load_config
from portfolio_snapshot import build_portfolio_positions, build_portfolio_snapshot
from pricing_providers import FundPrice
from transaction_analysis import TRANSACTION_SUMMARY_COLUMNS, analyze_transactions


def sample_transactions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "fund_code": "000001",
                "confirmed_units": 10.0,
                "confirmed_amount": 100.0,
                "fee": 1.0,
                "trade_date": "2024-01-01",
                "transaction_type": "Buy",
                "parent_strategy": "core",
                "child_strategy": "alpha",
            },
            {
                "fund_code": "000001",
                "confirmed_units": 0.0,
                "confirmed_amount": 10.0,
                "fee": 0.0,
                "trade_date": "2024-01-02",
                "transaction_type": "Income",
                "parent_strategy": "core",
                "child_strategy": None,
            },
            {
                "fund_code": "000001",
                "confirmed_units": 4.0,
                "confirmed_amount": 60.0,
                "fee": 0.0,
                "trade_date": "2024-01-03",
                "transaction_type": "Sell",
                "parent_strategy": "core",
                "child_strategy": None,
            },
            {
                "fund_code": "000001",
                "confirmed_units": 1.0,
                "confirmed_amount": 0.0,
                "fee": 0.0,
                "trade_date": "2024-01-04",
                "transaction_type": "Income",
                "parent_strategy": "core",
                "child_strategy": None,
            },
            {
                "fund_code": "000001",
                "confirmed_units": 2.0,
                "confirmed_amount": 20.0,
                "fee": 0.0,
                "trade_date": "2024-01-01",
                "transaction_type": "Buy",
                "parent_strategy": "satellite",
                "child_strategy": "beta",
            },
        ]
    )


def test_load_config_resolves_project_paths(tmp_path):
    project_root = tmp_path / "project"
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True)
    config_path = data_dir / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "reporting": {
                    "tracking_type": ["parent_strategy"],
                    "placeholder": [
                        {"fund_code": "cash"},
                        ["bond", "fixed_income", "short_term", 100.0],
                    ],
                },
                "pricing": {"provider": "fake"},
                "export": {"path": "backup"},
            }
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.tracking_keys == ("parent_strategy",)
    assert config.placeholders == (
        {"fund_code": "cash"},
        ["bond", "fixed_income", "short_term", 100.0],
    )
    assert config.pricing_provider_name == "fake"
    assert config.export_path == project_root / "backup"


def test_application_data_paths_are_project_constants():
    project_root = TRANSACTION_PATH.parents[1]

    assert TRANSACTION_PATH == project_root / "data" / "transactions.csv"
    assert TRANSACTION_CACHE_PATH == (
        project_root / ".cache" / "transaction-analysis.json"
    )


def test_analyze_transactions_preserves_position_algorithm():
    actual = analyze_transactions(sample_transactions())
    expected = pd.DataFrame(
        [
            ["000001", 60.6, 7.0, 8.6571, "core", "alpha", 6.0, 10.0, -41.0],
            ["000001", 20.0, 2.0, 10.0, "satellite", "beta", 0.0, 0.0, -20.0],
        ],
        columns=TRANSACTION_SUMMARY_COLUMNS,
    )

    pd.testing.assert_frame_equal(actual, expected)


def test_cache_reuses_summary_until_transaction_content_changes(tmp_path, monkeypatch):
    source_path = tmp_path / "transactions.csv"
    cache_path = tmp_path / "cache" / "transaction-analysis.json"
    transactions = sample_transactions()
    transactions.to_csv(source_path, index=False)

    real_analyze = transaction_cache.analyze_transactions
    calls = 0

    def counting_analyze(frame: pd.DataFrame) -> pd.DataFrame:
        nonlocal calls
        calls += 1
        return real_analyze(frame)

    monkeypatch.setattr(transaction_cache, "analyze_transactions", counting_analyze)

    first = transaction_cache.load_transaction_summary(source_path, cache_path)
    second = transaction_cache.load_transaction_summary(source_path, cache_path)
    assert calls == 1
    pd.testing.assert_frame_equal(first, second)

    transactions.loc[0, "confirmed_amount"] = 120.0
    transactions.to_csv(source_path, index=False)
    third = transaction_cache.load_transaction_summary(source_path, cache_path)
    assert calls == 2
    assert (
        third.loc[0, "total_investment_cost"] != first.loc[0, "total_investment_cost"]
    )

    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    assert payload["transaction_count"] == len(transactions)


def test_positions_are_available_without_pricing_provider(tmp_path):
    transaction_path = tmp_path / "transactions.csv"
    cache_path = tmp_path / "cache" / "summary.json"
    sample_transactions().to_csv(transaction_path, index=False)

    positions = build_portfolio_positions(
        transaction_path=transaction_path,
        transaction_cache_path=cache_path,
    )

    assert cache_path.exists()
    assert positions["holding_units"].tolist() == [7.0, 2.0]
    assert positions["average_cost_per_unit"].tolist() == [8.6571, 10.0]
    assert "market_value" not in positions


def test_snapshot_marks_valuation_missing_without_pricing_provider(tmp_path):
    transaction_path = tmp_path / "transactions.csv"
    cache_path = tmp_path / "cache" / "summary.json"
    sample_transactions().to_csv(transaction_path, index=False)
    config = AppConfig(
        tracking_keys=(),
        placeholders=(),
        pricing_provider_name=None,
        export_path=None,
    )

    snapshot = build_portfolio_snapshot(
        config,
        transaction_path=transaction_path,
        transaction_cache_path=cache_path,
    )

    assert "price_status" not in snapshot
    assert snapshot["market_value"].isna().all()
    assert snapshot["unrealized_pnl"].isna().all()


def test_snapshot_uses_injected_provider_and_cached_transaction_summary(tmp_path):
    transaction_path = tmp_path / "transactions.csv"
    sample_transactions().to_csv(transaction_path, index=False)
    config = AppConfig(
        tracking_keys=("parent_strategy",),
        placeholders=(),
        pricing_provider_name="fake",
        export_path=None,
    )
    transaction_cache_path = tmp_path / "cache" / "summary.json"

    class FakePricingProvider:
        name = "fake"

        def fetch_prices(self, fund_codes: list[str]) -> dict[str, FundPrice]:
            return {
                code: FundPrice(
                    fund_name=f"Fund {code}",
                    price_per_unit=12.5,
                )
                for code in fund_codes
            }

    snapshot = build_portfolio_snapshot(
        config,
        FakePricingProvider(),
        transaction_path=transaction_path,
        transaction_cache_path=transaction_cache_path,
    )

    assert transaction_cache_path.exists()
    assert snapshot["fund_name"].eq("Fund 000001").all()
    assert snapshot["price_per_unit"].eq(12.5).all()
    assert snapshot["market_value"].tolist() == [87.5, 25.0]
