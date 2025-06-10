import pandas as pd
import logging
from typing import Callable, List, Dict

class BacktestEngine:
    """Very simple backtesting engine using historical price data."""

    def __init__(self, prices: pd.DataFrame, strategy_fn: Callable[[List[float]], str]):
        self.prices = prices
        self.strategy_fn = strategy_fn
        self.trades = []
        self.equity = 1.0

    def run(self):
        history: List[float] = []
        for ts, row in self.prices.iterrows():
            price = row["close"]
            history.append(price)
            signal = self.strategy_fn(history)
            if signal == "buy":
                self.trades.append({"type": "buy", "price": price})
            elif signal == "sell" and self.trades:
                entry = self.trades[-1]["price"]
                pnl = price / entry - 1
                self.equity *= 1 + pnl
                self.trades.append({"type": "sell", "price": price, "pnl": pnl})
                logging.info(f"Trade closed pnl={pnl:.3f}")

    def summary(self) -> Dict:
        wins = [t for t in self.trades if t.get("pnl", 0) > 0]
        losses = [t for t in self.trades if t.get("pnl", 0) <= 0]
        return {
            "equity": self.equity,
            "trades": len(self.trades) // 2,
            "win_rate": len(wins) / max(len(wins) + len(losses), 1),
        }
