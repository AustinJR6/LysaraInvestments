import pandas as pd
import logging
from typing import Type
from backtest.backtest_engine import BacktestEngine


def run_backtest(strategy_cls: Type, csv_path: str) -> dict:
    """Load price CSV and run strategy on historical closes."""
    df = pd.read_csv(csv_path, parse_dates=[0])
    required = {'open', 'high', 'low', 'close', 'volume'}
    if not required.issubset(df.columns):
        raise ValueError(f'CSV must contain columns {required}')

    df.set_index(df.columns[0], inplace=True)

    def strategy_fn(history):
        strat = strategy_cls(None, None, {}, None, ['TEST'])  # simple instance
        if hasattr(strat, 'generate_signal'):
            return strat.generate_signal(history)
        return 'hold'

    engine = BacktestEngine(df, strategy_fn)
    engine.run()
    summary = engine.summary()
    logging.info(f"Backtest complete: {summary}")
    return summary
