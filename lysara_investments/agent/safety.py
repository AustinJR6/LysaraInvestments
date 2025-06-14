"""Safety checks for the Lysara agent."""

from __future__ import annotations

import logging
from typing import Dict

from db.db_manager import DatabaseManager


class SafetyMonitor:
    """Monitor trading activity and disable when limits hit."""

    def __init__(self, db: DatabaseManager, config: Dict):
        self.db = db
        self.config = config
        self.max_drawdown = config.get("max_drawdown", 0.12)
        self.max_position = config.get("max_position_size", 1.0)
        self.loss_streak_limit = config.get("max_loss_streak", 3)
        self.disabled = False
        self._loss_streak = 0
        self._start_equity = None

    def _get_recent_equity(self) -> float:
        cur = self.db.conn.cursor()
        cur.execute(
            "SELECT total_equity FROM equity_snapshots ORDER BY timestamp DESC LIMIT 1"
        )
        row = cur.fetchone()
        return float(row[0]) if row else 0.0

    def check_drawdown(self):
        equity = self._get_recent_equity()
        if self._start_equity is None:
            self._start_equity = equity
        if self._start_equity == 0:
            return
        dd = (equity - self._start_equity) / self._start_equity
        if dd <= -self.max_drawdown:
            logging.warning("Max drawdown exceeded – disabling trading")
            self.disabled = True

    def record_trade_result(self, pnl: float):
        if pnl < 0:
            self._loss_streak += 1
        else:
            self._loss_streak = 0
        if self._loss_streak >= self.loss_streak_limit:
            logging.warning("Loss streak limit hit – disabling trading")
            self.disabled = True

    def check(self):
        if self.disabled:
            return False
        self.check_drawdown()
        return not self.disabled

