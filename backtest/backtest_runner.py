import pandas as pd
import logging
from typing import Type
from backtest.backtest_engine import BacktestEngine


def run_backtest(strategy_cls: Type, csv_path: str) -> dict:
    """Load price CSV and run strategy on historical closes."""
    df = pd.read_csv(csv_path)
    if 'close' not in df.columns:
        raise ValueError('CSV must contain close column')

    def strategy_fn(prices):
        strat = strategy_cls(None, None, {}, None, [])  # simplified instance
        # use strategy's logic on history if method available
        if hasattr(strat, 'generate_signal'):
            return strat.generate_signal(prices)
        return 'hold'

    engine = BacktestEngine(df[['close']], strategy_fn)
    engine.run()
    summary = engine.summary()
    logging.info(f"Backtest complete: {summary}")
    return summary
