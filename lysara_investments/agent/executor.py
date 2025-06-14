"""Trade execution layer with optional approval and risk guardrails."""

from __future__ import annotations

import logging
from typing import Dict, Any

from api.crypto_api import CryptoAPI
from risk.risk_manager import RiskManager


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
            passphrase=api_keys.get("coinbase_passphrase", ""),
            simulation_mode=config.get("simulation_mode", True),
            config=config,
        )
        self.risk = RiskManager(self.api, config.get("crypto_settings", {}))

    async def execute(self, decision: Dict[str, Any], symbol: str):
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
        price_data = await self.api.fetch_market_price(symbol)
        price = float(price_data.get("price", 0))
        qty = self.risk.get_position_size(price)
        side = "buy" if action == "BUY" else "sell"
        logging.info(f"Executing {side} {qty} {symbol} @ {price}")
        result = await self.api.place_order(symbol, qty, side, confidence=decision.get("confidence"))
        return result

