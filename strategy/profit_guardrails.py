"""Safety checks for trading profits and drawdowns."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GuardrailState:
    daily_pl: float = 0.0
    disabled: bool = False


def update(state: GuardrailState, pnl: float, cfg: dict) -> None:
    """Update state with new trade PnL and enforce thresholds."""
    state.daily_pl += pnl
    if state.daily_pl <= -cfg.get("max_daily_loss_pct", 5) / 100:
        state.disabled = True

