"""Neural net trade direction classifier."""
from __future__ import annotations

from typing import Dict

try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover - xgboost optional
    XGBClassifier = None


class AITradeOracle:
    """Simple wrapper around an XGBoost classifier."""

    def __init__(self) -> None:
        self.model = XGBClassifier() if XGBClassifier else None

    def predict(self, features) -> Dict:
        """Return dummy prediction for now."""
        if not self.model:
            return {"action": "hold", "confidence": 0.0}
        # TODO: train model with proper dataset
        pred = self.model.predict_proba([features])[0]
        action = ["buy", "hold", "short"][pred.argmax()]
        return {"action": action, "confidence": float(pred.max())}

