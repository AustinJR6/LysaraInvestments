"""Asynchronous wrapper around the Coinbase Advanced Trade Python SDK."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Dict, List

from coinbase.rest import RESTClient


class CoinbaseClient:
    """Thin async wrapper for the Coinbase Advanced Trade RESTClient."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        simulation_mode: bool = True,
        portfolio=None,
        config: Dict | None = None,
        trade_cooldown: int = 30,
    ) -> None:
        self.simulation_mode = simulation_mode
        self.portfolio = portfolio
        self.config = config or {}
        self.trade_cooldown = trade_cooldown
        self._last_trade: Dict[str, float] = {}
        self._mock_equity = 10000.0
        self._mock_holdings: Dict[str, float] = {}

        self.client = None
        if not simulation_mode:
            # RESTClient is synchronous; wrap calls using asyncio.to_thread.
            self.client = RESTClient(api_key=api_key, api_secret=api_secret)

    async def _run(self, func, *args, **kwargs):
        """Execute a blocking SDK call in a thread."""
        return await asyncio.to_thread(func, *args, **kwargs)

    # ------------------------------------------------------------------
    # Account and holdings
    # ------------------------------------------------------------------
    async def fetch_account_info(self) -> Dict[str, Any]:
        """Return USD balance from Coinbase or mock data."""

        if self.simulation_mode:
            logging.debug(
                "CoinbaseClient: simulation_mode – returning mock account info"
            )
            return {"currency": "USD", "balance": self._mock_equity}

        data = await self._run(self.client.get_accounts)
        usd_balance = 0.0
        for acct in getattr(data, "accounts", []):
            if getattr(acct, "currency", "") == "USD" and acct.available_balance:
                bal = getattr(acct.available_balance, "value", 0) or 0
                usd_balance = float(bal)
                break
        return {"currency": "USD", "balance": usd_balance}

    async def fetch_holdings(self) -> Dict[str, float]:
        """Return holdings for each currency."""

        if self.simulation_mode:
            logging.debug(
                "CoinbaseClient: simulation_mode – returning mock holdings"
            )
            return self._mock_holdings

        data = await self._run(self.client.get_accounts)
        holdings: Dict[str, float] = {}
        for acct in getattr(data, "accounts", []):
            cur = getattr(acct, "currency", None)
            bal = getattr(acct, "available_balance", None)
            if bal is not None:
                bal_val = float(getattr(bal, "value", 0) or 0)
                if cur and bal_val:
                    holdings[cur] = bal_val
        return holdings

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------
    async def fetch_market_price(self, product_id: str) -> Dict[str, float]:
        """Get current bid/ask information for a product."""

        if self.simulation_mode:
            logging.debug(f"CoinbaseClient: sim price for {product_id}")
            return {"price": 0.0, "bid": 0.0, "ask": 0.0}

        data = await self._run(self.client.get_market_trades, product_id, 1)
        bid = float(getattr(data, "best_bid", 0) or 0)
        ask = float(getattr(data, "best_ask", 0) or 0)
        price = (bid + ask) / 2 if bid and ask else bid or ask
        return {"price": price, "bid": bid, "ask": ask}

    # ------------------------------------------------------------------
    # Order management
    # ------------------------------------------------------------------
    async def place_order(
        self,
        product_id: str,
        side: str,
        size: float,
        price: float | None = None,
        order_type: str = "market",
        **kwargs,
    ) -> Any:
        """Place an order using the SDK or simulate locally."""

        if not self.simulation_mode:
            now = asyncio.get_event_loop().time()
            last = self._last_trade.get(product_id)
            if last and now - last < self.trade_cooldown:
                logging.warning(f"Duplicate trade blocked for {product_id}")
                return {"status": "blocked", "reason": "duplicate"}
            self._last_trade[product_id] = now

        if self.simulation_mode:
            logging.info(
                f"CoinbaseClient: sim {order_type} order {side} {size} {product_id}"
            )
            trade_price = price
            if trade_price is None:
                data = await self.fetch_market_price(product_id)
                trade_price = float(data.get("price", 0))
            if self.portfolio:
                conf = kwargs.get("confidence", 0.0)
                self.portfolio.execute_trade(product_id, side, size, trade_price, conf)
            return {
                "id": "sim_order",
                "status": "done",
                "filled_size": size,
                "price": trade_price,
            }

        client_id = uuid.uuid4().hex
        if order_type == "market":
            if side.lower() == "buy":
                result = await self._run(
                    self.client.market_order_buy,
                    client_id,
                    product_id,
                    base_size=str(size),
                )
            else:
                result = await self._run(
                    self.client.market_order_sell,
                    client_id,
                    product_id,
                    base_size=str(size),
                )
        else:  # limit order
            if price is None:
                raise ValueError("Limit orders require a price")
            if side.lower() == "buy":
                result = await self._run(
                    self.client.limit_order_gtc_buy,
                    client_id,
                    product_id,
                    base_size=str(size),
                    limit_price=str(price),
                )
            else:
                result = await self._run(
                    self.client.limit_order_gtc_sell,
                    client_id,
                    product_id,
                    base_size=str(size),
                    limit_price=str(price),
                )

        trade_price = price if price is not None else 0.0
        if trade_price == 0.0:
            try:
                data = await self.fetch_market_price(product_id)
                trade_price = float(data.get("price", 0))
            except Exception:
                trade_price = 0.0

        from utils.guardrails import log_live_trade

        await log_live_trade(
            product_id,
            side,
            size,
            trade_price,
            self.config,
            market="crypto",
            confidence=kwargs.get("confidence"),
            risk_pct=self.config.get("crypto_settings", {}).get("risk_per_trade")
            * 100
            if self.config.get("crypto_settings")
            else None,
        )

        return result

    async def cancel_order(self, order_id: str) -> Any:
        """Cancel an order by ID."""
        if self.simulation_mode:
            logging.info(f"CoinbaseClient: sim cancel order {order_id}")
            return {"id": order_id, "status": "canceled"}
        return await self._run(self.client.cancel_orders, [order_id])

    async def check_order_fills(self, order_id: str) -> List[Dict[str, Any]]:
        """Return fills for an order."""
        if self.simulation_mode:
            return []
        data = await self._run(self.client.get_fills, order_ids=[order_id], limit=100)
        fills = []
        for fill in getattr(data, "fills", []):
            fills.append(fill.__dict__)
        return fills

