"""Simple decision engine combining sentiment and price signals."""

from __future__ import annotations

from typing import Dict, Any
import logging

from .market_snapshot import MarketSnapshot
from .personality import explain_decision


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


def make_trade_decision(snapshot: MarketSnapshot, config: Dict) -> Dict[str, Any]:
    """Return a trade decision dictionary."""
    sentiment_score = analyze_sentiment(snapshot)
    threshold = config.get("confidence_threshold", 0.7)

    action = "HOLD"
    confidence = abs(sentiment_score)
    if sentiment_score > 0.1:
        action = "BUY"
    elif sentiment_score < -0.1:
        action = "SELL"

    decision = {
        "action": action,
        "confidence": round(min(confidence, 1.0), 2),
        "rationale": f"Sentiment score {sentiment_score:.2f}",
    }

    decision["explanation"] = explain_decision(
        snapshot.ticker,
        decision["action"],
        decision["rationale"],
        decision["confidence"],
    )

    if decision["confidence"] < threshold:
        logging.info("Decision confidence below threshold")

    return decision

