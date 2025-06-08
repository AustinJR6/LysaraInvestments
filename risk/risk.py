from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple
import numpy as np

from .risk_manager import RiskManager

@dataclass
class StopLevels:
    stop: float
    target: float
    rr: float

class DynamicRisk:
    """Extension around RiskManager for dynamic sizing and stops."""

    def __init__(self, manager: RiskManager, atr_period: int = 14, vol_mult: float = 3.0):
        self.manager = manager
        self.atr_period = atr_period
        self.vol_mult = vol_mult

    def _volatility(self, prices: list[float]) -> float:
        if len(prices) < 2:
            return 0.0
        arr = np.diff(prices[-self.atr_period:])
        return float(np.std(arr))

    def position_size(self, price: float, confidence: float, prices: list[float]) -> float:
        base = self.manager.get_position_size(price)
        vol = self._volatility(prices) or 1.0
        size = base * max(confidence, 0.1) / vol
        return round(size, 6)

    def stop_levels(self, entry_price: float, side: str, prices: list[float], min_rr: float = 1.5) -> StopLevels:
        vol = self._volatility(prices)
        trail = vol * self.vol_mult
        if side == "buy":
            stop = max(entry_price - trail, 0)
            target = entry_price + trail * min_rr
        else:
            stop = entry_price + trail
            target = max(entry_price - trail * min_rr, 0)
        rr = abs(target - entry_price) / max(abs(entry_price - stop), 1e-6)
        return StopLevels(stop=stop, target=target, rr=rr)
