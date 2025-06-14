"""Trade execution layer with optional approval and risk guardrails."""

from __future__ import annotations

import logging
from typing import Dict, Any

from api.crypto_api import CryptoAPI
from risk.risk_manager import RiskManager
from .market_snapshot import MarketSnapshot
from .safety import is_safe_to_trade


class TradeExecutor:
    """Execute trade decisions using existing service classes."""

    def __init__(self, config: Dict):
        self.config = config
        self.approval_required = config.get("approval_required", True)
        self.pending_decision: Dict[str, Any] | None = None

        api_keys = config.get("api_keys", {})
        self.api = CryptoAPI(
            api_key=api_keys.get("coinbase", ""),
            secret_key=api_keys.get("coinbase_secret", ""),
            simulation_mode=config.get("simulation_mode", True),
            config=config,
        )
        self.risk = RiskManager(self.api, config.get("crypto_settings", {}))

    async def execute(self, snapshot: MarketSnapshot, decision: Dict[str, Any]):
        """Execute the trade if allowed."""
        action = decision.get("action", "HOLD").upper()
        if action not in {"BUY", "SELL"}:
            logging.info("No trade action taken")
            return None

        if self.approval_required and not decision.get("approved", False):
            self.pending_decision = decision
            logging.info("Trade awaiting approval")
            return None

        await self.risk.update_equity()
        balance = self.risk.last_equity or 0
        start = self.risk.start_equity or balance
        recent_drawdown = 0.0
        if start:
            recent_drawdown = (start - balance) / start
        if not is_safe_to_trade(balance, recent_drawdown, decision.get("confidence", 0)):
            logging.warning("Trade blocked by safety rules")
            return None

        price = snapshot.price
        qty = self.risk.get_position_size(price)
        side = "buy" if action == "BUY" else "sell"
        logging.info(f"Executing {side} {qty} {snapshot.ticker} @ {price}")
        result = await self.api.place_order(snapshot.ticker, qty, side, confidence=decision.get("confidence"))
        return result

