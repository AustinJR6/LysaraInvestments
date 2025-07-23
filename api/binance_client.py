# api/binance_client.py
"""Async Binance client for core trading operations using Binance.US."""

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
        # Use Binance.US for all REST API calls
        base_url: str = "https://api.binance.us",
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
        """Send an authenticated request handling common Binance errors."""

        # Log the raw parameters and base URL for visibility before any mutation.
        logging.debug(
            "Preparing Binance signed request %s %s with params: %s",
            method,
            f"{self.base_url}{path}",
            params,
        )

        # Binance requires the HMAC SHA256 signature to be generated from the
        # exact query string that is sent with the request. Parameters are first
        # URL encoded then hashed using the API secret key.

        # Filter out ``None`` values and append the current timestamp. Binance
        # will reject requests if the timestamp is too far from their server
        # time, so ensure the system clock is reasonably synchronized.
        clean_params = {k: v for k, v in params.items() if v is not None}
        clean_params["timestamp"] = int(time.time() * 1000)
        logging.debug("Clean params: %s", clean_params)

        # Construct the query string in a deterministic order before signing
        query = urlencode(sorted(clean_params.items()), doseq=True)
        logging.debug("Query string for signature: %s", query)

        # HMAC-SHA256 signature of the query string using the API secret
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        logging.debug("Generated signature: %s", signature)

        # Final signed URL used for the request
        url = f"{self.base_url}{path}?{query}&signature={signature}"
        logging.debug("Final signed URL: %s", url)

        backoff = 1
        for attempt in range(1, 6):
            try:
                if method == "GET":
                    resp = await self.session.get(url)
                elif method == "DELETE":
                    resp = await self.session.delete(url)
                else:
                    resp = await self.session.post(url)

                data = await resp.json()

                if resp.status == 429 or data.get("code") in {-1003, -1015}:
                    logging.warning(
                        f"Binance rate limit hit (attempt {attempt}); retrying in {backoff}s"
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 32)
                    continue

                if resp.status >= 500:
                    logging.warning(
                        f"Binance server error {resp.status} (attempt {attempt}); retrying in {backoff}s"
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 32)
                    continue

                resp.raise_for_status()

                if data.get("code") and data.get("code") != 0:
                    code = int(data["code"])
                    msg = data.get("msg", "")
                    if code == -2010:
                        logging.error("Binance error: insufficient funds")
                    elif code == -1121:
                        logging.error("Binance error: invalid symbol")
                    else:
                        logging.error(f"Binance error {code}: {msg}")
                    return {"error": code, "message": msg}

                return data

            except aiohttp.ClientError as e:
                logging.warning(
                    f"Binance network error on {method} {path} (attempt {attempt}): {e}."
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 32)
            except Exception as e:  # pragma: no cover - unexpected
                logging.exception(f"Unexpected Binance error: {e}")
                return {"error": "exception", "message": str(e)}

        logging.error(f"Binance {method} {path} failed after {attempt} attempts")
        return {"error": "max_retries"}

    # ------------------------------------------------------------------
    # Account and holdings
    # ------------------------------------------------------------------
    async def fetch_account_info(self) -> Dict[str, Any]:
        if self.simulation_mode:
            logging.debug("BinanceClient: simulation mode – returning mock account info")
            return {"balance": self._mock_equity}
        data = await self._signed_request("GET", "/api/v3/account", {})
        balances = {
            b.get("asset"): float(b.get("free", 0))
            for b in data.get("balances", [])
            if float(b.get("free", 0)) > 0
        }
        data["parsed_balances"] = balances
        for stable in ("USDT", "USD", "BUSD", "USDC"):
            if stable in balances:
                data["balance"] = balances[stable]
                break
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
        if result.get("error"):
            return result
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
        result = await self._signed_request("DELETE", "/api/v3/order", params)
        return result

    async def close(self) -> None:
        await super().close()
