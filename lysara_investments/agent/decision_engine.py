"""Decision engine combining sentiment, technicals and risk checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import logging

from .market_snapshot import MarketSnapshot
from .personality import explain_decision
from risk.risk_manager import RiskManager


@dataclass
class DecisionInputs:
    """Container for all data required to make a decision."""

    snapshot: MarketSnapshot
    portfolio: Dict[str, Any] = field(default_factory=dict)
    risk_params: Dict[str, Any] = field(default_factory=dict)
    external_ai: Optional[Dict[str, Any]] = None


def analyze_sentiment(snapshot: MarketSnapshot) -> float:
    """Return average sentiment score from snapshot."""

    scores = []
    for source in snapshot.sentiment.values():
        if isinstance(source, dict):
            for val in source.values():
                score = val.get("score")
                if score is not None:
                    scores.append(score)
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def evaluate_technicals(technicals: Dict[str, Any]) -> float:
    """Return a simplified technical bias score in [-1, 1]."""

    bias = 0.0
    rsi = technicals.get("rsi")
    if isinstance(rsi, (int, float)):
        if rsi < 30:
            bias += 0.5
        elif rsi > 70:
            bias -= 0.5

    ma_cross = technicals.get("ma_cross")
    if ma_cross == "bullish" or ma_cross is True:
        bias += 0.5
    elif ma_cross == "bearish":
        bias -= 0.5

    return max(min(bias, 1.0), -1.0)


class DecisionEngine:
    """Core logic for generating trade decisions."""

    def __init__(self, config: Dict, risk_manager: Optional[RiskManager] = None):
        self.config = config
        self.risk = risk_manager

    # ------------------------------------------------------------------
    def _combine_signals(self, sentiment: float, technical: float) -> float:
        """Combine sentiment and technical scores into a composite value."""

        s_weight = self.config.get("sentiment_weight", 0.6)
        t_weight = self.config.get("technical_weight", 0.4)
        return (sentiment * s_weight) + (technical * t_weight)

    # ------------------------------------------------------------------
    def _assess_risk(self, action: str, price: float) -> Dict[str, Any]:
        """Return sizing and stop levels if a RiskManager is available."""

        size = 0.0
        stop = None
        target = None
        if self.risk:
            size = self.risk.get_position_size(price)
            sl_pct = self.config.get("stop_loss_pct", 0.01)
            tp_pct = self.config.get("take_profit_pct", 0.02)
            if action == "BUY":
                stop = round(price * (1 - sl_pct), 4)
                target = round(price * (1 + tp_pct), 4)
            elif action == "SELL":
                stop = round(price * (1 + sl_pct), 4)
                target = round(price * (1 - tp_pct), 4)

        return {
            "position_size": size,
            "stop_loss": stop,
            "take_profit": target,
        }

    # ------------------------------------------------------------------
    def _apply_external_ai(self, decision: Dict[str, Any], ai: Optional[Dict[str, Any]]):
        """Adjust decision based on external AI recommendation if provided."""

        if not ai:
            return

        ai_action = ai.get("action")
        ai_conf = ai.get("confidence", 0.0)
        reason = ai.get("reason", "external AI input")

        if ai_action and ai_conf >= decision["confidence"]:
            decision["action"] = ai_action.upper()
            decision["confidence"] = ai_conf
            decision["reasoning"] += f" | {reason}"
        else:
            decision["reasoning"] += " | external AI considered"

    # ------------------------------------------------------------------
    def decide(self, inputs: DecisionInputs) -> Dict[str, Any]:
        """Generate a trade decision based on provided inputs."""

        snapshot = inputs.snapshot
        sentiment = analyze_sentiment(snapshot)
        technical = evaluate_technicals(snapshot.technicals)
        composite = self._combine_signals(sentiment, technical)

        threshold = self.config.get("confidence_threshold", 0.7)
        action = "HOLD"
        if composite > self.config.get("buy_threshold", 0.2):
            action = "BUY"
        elif composite < self.config.get("sell_threshold", -0.2):
            action = "SELL"

        confidence = round(min(abs(composite), 1.0), 2)

        decision = {
            "action": action,
            "symbol": snapshot.ticker,
            "entry_price": snapshot.price,
            "confidence": confidence,
            "reasoning": f"sentiment={sentiment:.2f}, technical={technical:.2f}",
        }

        # backwards compatible key used in earlier versions
        decision["rationale"] = decision["reasoning"]

        decision.update(self._assess_risk(action, snapshot.price))
        self._apply_external_ai(decision, inputs.external_ai)

        decision["order"] = {
            "market": self.config.get("market", "crypto"),
            "symbol": snapshot.ticker,
            "side": decision["action"].lower(),
            "qty": decision.get("position_size", 0.0),
            "price": snapshot.price,
            "confidence": decision["confidence"],
        }

        decision["explanation"] = explain_decision(
            snapshot.ticker,
            decision["action"],
            decision["reasoning"],
            decision["confidence"],
        )

        if decision["confidence"] < threshold:
            logging.info("Decision confidence below threshold")

        return decision


def make_trade_decision(
    snapshot: MarketSnapshot,
    config: Dict,
    context: Optional[Dict[str, Any]] | None = None,
    risk_manager: Optional[RiskManager] = None,
) -> Dict[str, Any]:
    """Backward compatible helper for creating a DecisionEngine and running it."""

    inputs = DecisionInputs(
        snapshot=snapshot,
        portfolio=(context or {}).get("portfolio", {}),
        risk_params=(context or {}).get("risk_params", {}),
        external_ai=(context or {}).get("external_ai"),
    )

    engine = DecisionEngine(config, risk_manager)
    return engine.decide(inputs)


