import pandas as pd
import numpy as np
import logging
from dataclasses import dataclass
from typing import Callable, List, Dict, Optional
from pathlib import Path


@dataclass
class Trade:
    """Simple trade container for backtest results."""

    entry_time: pd.Timestamp
    exit_time: Optional[pd.Timestamp]
    entry_price: float
    exit_price: Optional[float]
    size: float
    pnl: Optional[float] = None


class RiskManager:
    """Handle position sizing based on equity and risk percent."""

    def __init__(self, risk_pct: float = 0.01):
        self.risk_pct = risk_pct

    def get_size(self, equity: float, price: float) -> float:
        dollar_risk = equity * self.risk_pct
        if price <= 0:
            return 0.0
        return round(dollar_risk / price, 8)

class BacktestEngine:
    """Backtesting engine with basic risk management and reporting."""

    REQUIRED_COLS = {"open", "high", "low", "close", "volume"}

    def __init__(
        self,
        prices: pd.DataFrame,
        strategy_fn: Callable[[List[float]], str],
        initial_balance: float = 10_000.0,
        risk_pct: float = 0.01,
        slippage: float = 0.0005,
        commission: float = 0.001,
        results_dir: str = "backtest/results",
    ) -> None:
        if not BacktestEngine.REQUIRED_COLS.issubset(prices.columns):
            raise ValueError(
                f"prices DataFrame must contain columns {BacktestEngine.REQUIRED_COLS}"
            )
        if not isinstance(prices.index, pd.DatetimeIndex):
            raise ValueError("prices index must be DatetimeIndex")

        self.prices = prices
        self.strategy_fn = strategy_fn
        self.balance = float(initial_balance)
        self.risk = RiskManager(risk_pct)
        self.slippage = slippage
        self.commission = commission
        self.results_dir = Path(results_dir)

        self.trades: List[Trade] = []
        self.open_trade: Optional[Trade] = None
        self.equity_curve: List[float] = []

    def run(self) -> None:
        history: List[float] = []
        for ts, row in self.prices.iterrows():
            price = float(row["close"])
            history.append(price)

            if self.open_trade:
                open_pnl = (price - self.open_trade.entry_price) * self.open_trade.size
                equity = self.balance + open_pnl
            else:
                equity = self.balance
            self.equity_curve.append(equity)

            signal = self.strategy_fn(history)

            if signal == "buy" and self.open_trade is None:
                size = self.risk.get_size(equity, price)
                if size > 0:
                    entry = price * (1 + self.slippage)
                    cost = entry * size * (1 + self.commission)
                    self.balance -= cost
                    self.open_trade = Trade(ts, None, entry, None, size)
            elif signal == "sell" and self.open_trade is not None:
                exit_price = price * (1 - self.slippage)
                pnl = (exit_price - self.open_trade.entry_price) * self.open_trade.size
                fees = (exit_price * self.open_trade.size) * self.commission
                self.balance += exit_price * self.open_trade.size - fees
                self.open_trade.exit_time = ts
                self.open_trade.exit_price = exit_price
                self.open_trade.pnl = pnl - (self.open_trade.entry_price * self.open_trade.size * self.commission)
                self.trades.append(self.open_trade)
                logging.info(f"Trade closed pnl={self.open_trade.pnl:.2f}")
                self.open_trade = None

        self._save_results()

    def _save_results(self) -> None:
        self.results_dir.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame({"equity": self.equity_curve}, index=self.prices.index[: len(self.equity_curve)])
        path = self.results_dir / "backtest_results.csv"
        df.to_csv(path)

    def summary(self) -> Dict:
        if not self.equity_curve:
            return {}

        equity = self.equity_curve[-1]
        pnl_list = [t.pnl for t in self.trades if t.pnl is not None]
        wins = [p for p in pnl_list if p > 0]
        losses = [p for p in pnl_list if p <= 0]
        daily_returns = np.diff(self.equity_curve) / self.equity_curve[:-1]
        max_drawdown = 0.0
        peak = self.equity_curve[0]
        for val in self.equity_curve:
            if val > peak:
                peak = val
            dd = (peak - val) / peak
            max_drawdown = max(max_drawdown, dd)
        sharpe = 0.0
        if daily_returns.size > 1 and np.std(daily_returns) != 0:
            sharpe = (np.mean(daily_returns) - 0.02) / np.std(daily_returns)
        profit_factor = abs(sum(wins)) / abs(sum(losses)) if losses else float('inf')

        return {
            "equity": equity,
            "trades": len(pnl_list),
            "win_rate": len(wins) / max(len(wins) + len(losses), 1),
            "avg_gain": np.mean(wins) if wins else 0.0,
            "avg_loss": np.mean(losses) if losses else 0.0,
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_drawdown,
        }
