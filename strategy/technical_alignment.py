"""Technical analysis alignment with sentiment."""
from __future__ import annotations

from typing import Dict
import pandas as pd

try:
    import ta
except Exception:  # pragma: no cover - ta optional
    ta = None


def check_alignment(df: pd.DataFrame, sentiment_label: str) -> bool:
    """Return True if technicals align with sentiment."""
    if ta is None or df.empty:
        return False
    rsi = ta.momentum.rsi(df["close"], window=14).iloc[-1]
    macd = ta.trend.macd(df["close"]).iloc[-1]
    if sentiment_label == "positive" and rsi < 30 and macd > 0:
        return True
    return False

