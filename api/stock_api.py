# ==============================
# api/stock_api.py
# ==============================

import logging
from urllib.parse import urljoin
import aiohttp
import asyncio
from api.base_api import BaseAPI

class StockAPI(BaseAPI):
    """
    Stock trading API client (e.g., Robinhood). Subclasses BaseAPI for HTTP logic.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str = None,
        base_url: str = "https://api.robinhood.com",
        simulation_mode: bool = True,
    ):
        super().__init__(base_url)
        self.api_key = api_key
        self.api_secret = api_secret
        self.simulation_mode = simulation_mode
        # For Robinhood, token auth might go here
        if not simulation_mode:
            # Example header for real-world usage
            self.session.headers.update({
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "application/json",
            })

    async def fetch_account_info(self) -> dict:
        """
        Return account balances or mock in simulation.
        """
        if self.simulation_mode:
            logging.debug("StockAPI: simulation mode – returning mock account info")
            return {"cash": 10000.0, "portfolio_value": 10000.0}
        path = "/accounts/"
        return await self.get(path)

    async def fetch_holdings(self) -> dict:
        """
        Return open positions or mock in simulation.
        """
        if self.simulation_mode:
            logging.debug("StockAPI: simulation mode – returning mock holdings")
            return {}
        path = "/positions/"
        data = await self.get(path)
        positions = {}
        for item in data.get("results", []):
            symbol = item.get("instrument", "")
            qty = float(item.get("quantity", 0))
            positions[symbol] = qty
        return positions

    async def fetch_market_price(self, symbol: str) -> dict:
        """
        Get latest bid/ask or mock.
        """
        if self.simulation_mode:
            logging.debug(f"StockAPI: sim price for {symbol}")
            return {"symbol": symbol, "bid": 0.0, "ask": 0.0, "last_trade_price": 0.0}
        path = f"/quotes/?symbols={symbol}"
        return await self.get(path)

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float = None,
        order_type: str = "market",
    ) -> dict:
        """
        Place market or limit order; returns order details or mock.
        """
        if self.simulation_mode:
            logging.info(f"StockAPI: sim {order_type} order {side} {quantity} {symbol}")
            return {"id": "sim_order", "status": "filled", "symbol": symbol, "side": side, "quantity": quantity}

        path = "/orders/"
        body = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "type": order_type,
        }
        if order_type == "limit" and price is not None:
            body["price"] = price
        return await self.post(path, body)

    async def close(self):
        """Clean up HTTP session."""
        await super().close()
