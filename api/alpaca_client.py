"""Async Alpaca trading client using alpaca-trade-api."""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Optional

import alpaca_trade_api as tradeapi

from utils.guardrails import log_live_trade


class AlpacaClient:
    """Thin async wrapper around the Alpaca REST API."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://paper-api.alpaca.markets",
        simulation_mode: bool = True,
        portfolio=None,
        config: Optional[Dict] = None,
        trade_cooldown: int = 30,
    ) -> None:
        self.simulation_mode = simulation_mode
        self.portfolio = portfolio
        self.config = config or {}
        self.trade_cooldown = trade_cooldown
        self._last_trade: Dict[str, float] = {}
        self._mock_equity = 10000.0
        self._mock_positions: Dict[str, float] = {}

        self.client = None
        if not simulation_mode:
            self.client = tradeapi.REST(
                api_key, api_secret, base_url, api_version="v2"
            )

    async def _run(self, func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

    # ------------------------------------------------------------------
    # Account and positions
    # ------------------------------------------------------------------
    async def get_account_info(self) -> Dict:
        if self.simulation_mode:
            logging.debug("AlpacaClient: returning mock account info")
            return {"equity": self._mock_equity}
        for attempt in range(1, 4):
            try:
                acct = await self._run(self.client.get_account)
                return acct.__dict__
            except Exception as e:
                logging.error(
                    f"get_account_info failed (attempt {attempt}): {e}"
                )
                await asyncio.sleep(attempt)
        return {}

    async def get_stock_holdings(self) -> Dict[str, float]:
        if self.simulation_mode:
            logging.debug("AlpacaClient: returning mock positions")
            return self._mock_positions
        for attempt in range(1, 4):
            try:
                positions = await self._run(self.client.list_positions)
                result: Dict[str, float] = {}
                for p in positions:
                    result[p.symbol] = float(p.qty)
                return result
            except Exception as e:
                logging.error(
                    f"get_stock_holdings failed (attempt {attempt}): {e}"
                )
                await asyncio.sleep(attempt)
        return {}

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------
    async def place_order(
        self, symbol: str, side: str, qty: float, order_type: str = "market"
    ) -> Dict:
        if self.simulation_mode:
            logging.info(f"[SIM] {side.upper()} {qty} {symbol}")
            price = 0.0
            if self.portfolio:
                price = (
                    await self.fetch_market_price(symbol)
                ).get("price", 0.0)
                self.portfolio.execute_trade(symbol, side, qty, price)
            return {"id": "sim", "status": "filled", "symbol": symbol, "qty": qty}

        now = asyncio.get_event_loop().time()
        last = self._last_trade.get(symbol)
        if last and now - last < self.trade_cooldown:
            logging.warning(f"Duplicate trade blocked for {symbol}")
            return {"status": "blocked"}
        self._last_trade[symbol] = now

        for attempt in range(1, 4):
            try:
                order = await self._run(
                    self.client.submit_order,
                    symbol=symbol,
                    qty=qty,
                    side=side,
                    type=order_type,
                    time_in_force="day",
                )
                price = (
                    await self.fetch_market_price(symbol)
                ).get("price", 0.0)
                await log_live_trade(
                    symbol,
                    side,
                    qty,
                    price,
                    self.config,
                    market="stock",
                )
                return order.__dict__ if hasattr(order, "__dict__") else order
            except Exception as e:
                logging.error(
                    f"place_order failed (attempt {attempt}): {e}"
                )
                await asyncio.sleep(attempt)
        return {"status": "error"}

    async def fetch_market_price(self, symbol: str) -> Dict:
        if self.simulation_mode:
            return {"price": 0.0}
        for attempt in range(1, 4):
            try:
                trade = await self._run(self.client.get_latest_trade, symbol)
                return {"price": float(trade.price)}
            except Exception as e:
                logging.error(
                    f"fetch_market_price failed (attempt {attempt}): {e}"
                )
                await asyncio.sleep(attempt)
        return {"price": 0.0}
