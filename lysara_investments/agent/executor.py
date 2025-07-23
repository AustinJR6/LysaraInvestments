"""Trade execution layer with optional approval and risk guardrails."""

from __future__ import annotations

import logging
from typing import Dict, Any

from risk.risk_manager import RiskManager
from services.trade_executor import TradeExecutorService
from api.crypto_api import CryptoAPI
from .market_snapshot import MarketSnapshot
from .safety import is_safe_to_trade


class TradeExecutor:
    """Execute trade decisions using existing service classes."""

    def __init__(self, config: Dict):
        self.config = config
        self.approval_required = config.get("approval_required", True)
        self.pending_decision: Dict[str, Any] | None = None

        self.service = TradeExecutorService(config)
        self.api_client = getattr(self.service, "crypto_api", None)
        self.risk = RiskManager(self.api_client or CryptoAPI(), config.get("crypto_settings", {}))

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

        signal = decision.get("order") or {
            "market": "crypto",
            "symbol": snapshot.ticker,
            "side": action.lower(),
            "qty": self.risk.get_position_size(snapshot.price),
            "price": snapshot.price,
            "confidence": decision.get("confidence"),
        }
        logging.info(
            f"Executing {signal['side']} {signal['qty']} {signal['symbol']} @ {signal['price']}"
        )
        if not self.config.get("ENABLE_AI_TRADE_EXECUTION", False):
            logging.info("AI trade execution disabled. Signal logged only.")
            return None
        await self.service.execute_order(signal)
        return signal

