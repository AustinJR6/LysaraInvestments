# api/binance_client.py
"""Async Binance client for core trading operations."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import aiohttp

from api.base_api import BaseAPI
from utils.guardrails import log_live_trade


class BinanceClient(BaseAPI):
    """Simplified async client for the Binance REST API."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://api.binance.com",
        simulation_mode: bool = True,
        portfolio=None,
        config: Optional[Dict] = None,
        trade_cooldown: int = 30,
    ) -> None:
        super().__init__(base_url)
        self.api_key = api_key
        self.api_secret = api_secret
        self.simulation_mode = simulation_mode
        self.portfolio = portfolio
        self.config = config or {}
        self.trade_cooldown = trade_cooldown
        self._last_trade: Dict[str, float] = {}
        self._mock_equity = 10000.0
        self._mock_holdings: Dict[str, float] = {}
        if not simulation_mode:
            self.session.headers.update({"X-MBX-APIKEY": api_key})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    async def _signed_request(self, method: str, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        params["timestamp"] = int(time.time() * 1000)
        query = urlencode(params, True)
        signature = hmac.new(self.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        query += f"&signature={signature}"
        url = f"{self.base_url}{path}?{query}"
        for attempt in range(1, 4):
            try:
                if method == "GET":
                    resp = await self.session.get(url)
                else:
                    resp = await self.session.post(url)
                resp.raise_for_status()
                return await resp.json()
            except Exception as e:
                logging.error(f"Binance {method} {path} failed (attempt {attempt}): {e}")
                await asyncio.sleep(attempt)
        return {}

    # ------------------------------------------------------------------
    # Account and holdings
    # ------------------------------------------------------------------
    async def fetch_account_info(self) -> Dict[str, Any]:
        if self.simulation_mode:
            logging.debug("BinanceClient: simulation mode – returning mock account info")
            return {"balance": self._mock_equity}
        data = await self._signed_request("GET", "/api/v3/account", {})
        return data

    async def get_holdings(self) -> Dict[str, float]:
        if self.simulation_mode:
            logging.debug("BinanceClient: simulation mode – returning mock holdings")
            return self._mock_holdings
        data = await self._signed_request("GET", "/api/v3/account", {})
        holdings: Dict[str, float] = {}
        for bal in data.get("balances", []):
            asset = bal.get("asset")
            free = float(bal.get("free", 0))
            if asset and free:
                holdings[asset] = free
        return holdings

    # ------------------------------------------------------------------
    # Market Data
    # ------------------------------------------------------------------
    async def fetch_market_price(self, symbol: str) -> Dict[str, float]:
        if self.simulation_mode:
            return {"price": 0.0, "bid": 0.0, "ask": 0.0}
        sym = symbol.replace("-", "")
        for attempt in range(1, 4):
            try:
                url = f"{self.base_url}/api/v3/ticker/bookTicker?symbol={sym}"
                async with self.session.get(url) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                bid = float(data.get("bidPrice", 0))
                ask = float(data.get("askPrice", 0))
                price = (bid + ask) / 2 if bid and ask else bid or ask
                return {"price": price, "bid": bid, "ask": ask}
            except Exception as e:
                logging.error(f"fetch_market_price failed (attempt {attempt}): {e}")
                await asyncio.sleep(attempt)
        return {"price": 0.0, "bid": 0.0, "ask": 0.0}

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------
    async def place_order(
        self, symbol: str, side: str, qty: float, order_type: str = "MARKET", **kwargs
    ) -> Any:
        if self.simulation_mode:
            logging.info(f"BinanceClient SIM {side} {qty} {symbol}")
            price = 0.0
            if self.portfolio:
                price = (await self.fetch_market_price(symbol)).get("price", 0.0)
                self.portfolio.execute_trade(symbol, side, qty, price, kwargs.get("confidence", 0.0))
            return {"orderId": "sim_order", "status": "FILLED", "executedQty": qty}

        now = asyncio.get_event_loop().time()
        last = self._last_trade.get(symbol)
        if last and now - last < self.trade_cooldown:
            logging.warning(f"Duplicate trade blocked for {symbol}")
            return {"status": "blocked"}
        self._last_trade[symbol] = now

        params = {
            "symbol": symbol.replace("-", ""),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": qty,
        }
        result = await self._signed_request("POST", "/api/v3/order", params)
        price = (await self.fetch_market_price(symbol)).get("price", 0.0)
        await log_live_trade(
            symbol,
            side,
            qty,
            price,
            self.config,
            market="crypto",
            confidence=kwargs.get("confidence"),
        )
        return result

    async def cancel_order(self, symbol: str, order_id: str) -> Any:
        if self.simulation_mode:
            logging.info(f"BinanceClient SIM cancel {order_id}")
            return {"orderId": order_id, "status": "CANCELED"}
        params = {"symbol": symbol.replace("-", ""), "orderId": order_id}
        return await self._signed_request("DELETE", "/api/v3/order", params)

    async def close(self) -> None:
        await super().close()
