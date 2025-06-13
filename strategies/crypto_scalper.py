from __future__ import annotations

from typing import List

from indicators.technical_indicators import relative_strength_index


class CryptoScalper:
    """Simple RSI based micro-scalping strategy."""

    def __init__(self, api, risk, config, db, symbols):
        self.config = config or {}
        self.rsi_threshold = self.config.get("scalp_rsi_buy_threshold", 30)
        self.profit_target = self.config.get("scalp_profit_target_pct", 0.75) / 100
        self.timeout = self.config.get("scalp_timeout_minutes", 10)
        self.in_position = False
        self.entry_price = 0.0
        self.entry_index = 0

    def generate_signal(self, history: List[float]) -> str:
        if self.in_position:
            hold_time = len(history) - self.entry_index
            if (
                history[-1] >= self.entry_price * (1 + self.profit_target)
                or hold_time >= self.timeout
            ):
                self.in_position = False
                return "sell"
            return "hold"

        if len(history) < 15:
            return "hold"
        rsi = relative_strength_index(history, 14)
        if rsi < self.rsi_threshold and history[-1] > history[-2] and history[-1] > history[-2] and history[-1] > 0:
            self.in_position = True
            self.entry_price = history[-1]
            self.entry_index = len(history)
            return "buy"
        return "hold"
