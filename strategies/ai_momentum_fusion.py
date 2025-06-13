from __future__ import annotations

import asyncio
from typing import List

from services.ai_strategist import get_conviction_score
from signals.sentiment_manager import get_sentiment_score


class AIMomentumFusion:
    """AI-Driven momentum strategy combining sentiment and conviction."""

    def __init__(self, api, risk, config, db, symbols):
        self.config = config or {}
        self.gpt4o_enabled = self.config.get("gpt4o_enabled", False)
        self.min_conviction = self.config.get("min_conviction_score", 0.7)
        self.window = self.config.get("momentum_window", 3)
        self.in_position = False
        self.symbol = symbols[0] if symbols else "BTC-USD"

    def _ai_score(self, context: dict) -> float:
        if not self.gpt4o_enabled:
            return 0.5
        try:
            return asyncio.run(get_conviction_score(context))
        except Exception:
            return 0.5

    def generate_signal(self, history: List[float]) -> str:
        if len(history) <= self.window:
            return "hold"
        momentum = (history[-1] - history[-self.window]) / history[-self.window]
        sentiment = get_sentiment_score(self.symbol)
        score = self._ai_score({"momentum": momentum, "sentiment": sentiment})

        if self.in_position:
            if momentum <= 0 or score < self.min_conviction or sentiment <= 0:
                self.in_position = False
                return "sell"
            return "hold"
        else:
            if momentum > 0 and score >= self.min_conviction and sentiment > 0:
                self.in_position = True
                return "buy"
        return "hold"
