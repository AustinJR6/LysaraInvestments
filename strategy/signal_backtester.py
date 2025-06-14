"""Backtest sentiment + TA signals."""
from __future__ import annotations

from typing import List, Dict
import pandas as pd


def backtest(df: pd.DataFrame, signal: pd.Series) -> Dict:
    """Very simple backtest using signal as position indicator."""
    returns = df["close"].pct_change().fillna(0)
    strat_returns = returns * signal.shift(1).fillna(0)
    equity_curve = (1 + strat_returns).cumprod()
    win_pct = (strat_returns > 0).mean()
    total_return = equity_curve.iloc[-1] - 1
    sharpe = (strat_returns.mean() / strat_returns.std()) * (252 ** 0.5) if strat_returns.std() else 0
    return {
        "win_pct": float(win_pct),
        "total_return": float(total_return),
        "sharpe": float(sharpe),
    }

