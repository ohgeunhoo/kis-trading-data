"""Week14 notebook setup helpers.

Student notebooks import from here so the visible setup cell stays short.
"""

from src.kis_client import get_token, load_env
from labs.lab03_order import fetch_account_summary, fetch_balance, place_order

load_env()


def __getattr__(name: str):
    """Lazy-load heavier Week14 helpers on demand.

    The notebook's first setup cell only needs token/account/order helpers.
    Importing backtest/strategy modules eagerly would pull in optional packages
    like pandas before the student actually needs them.
    """
    if name == "backtest":
        from labs.lab04_backtest_demo import backtest

        return backtest
    if name in {
        "account_value",
        "ETF_CODES",
        "sample_prices",
        "build_rebalance_orders",
        "mock_rebalance_submit",
        "strategy",
        "weights_to_target_qty",
    }:
        from labs.lab05_strategy_kis import (
            ACCOUNT_VALUE_DEFAULT as account_value,
            ETF_CODES,
            _SAMPLE_PRICES as sample_prices,
            build_rebalance_orders,
            mock_rebalance_submit,
            strategy,
            weights_to_target_qty,
        )

        return {
            "account_value": account_value,
            "ETF_CODES": ETF_CODES,
            "sample_prices": sample_prices,
            "build_rebalance_orders": build_rebalance_orders,
            "mock_rebalance_submit": mock_rebalance_submit,
            "strategy": strategy,
            "weights_to_target_qty": weights_to_target_qty,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
