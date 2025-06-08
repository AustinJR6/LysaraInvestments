# api/crypto_api.py

import time
import hmac
import hashlib
import base64
import json
import logging
from api.base_api import BaseAPI

class CryptoAPI(BaseAPI):
    """
    Coinbase API client for REST calls (live & simulation).
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str = None,
        passphrase: str = None,
        base_url: str = "https://api.pro.coinbase.com",
        simulation_mode: bool = True,
        portfolio=None,
    ):
        super().__init__(base_url)
        self.api_key = api_key
        self.secret_key = secret_key or ""
        self.passphrase = passphrase or ""
        self.simulation_mode = simulation_mode
        self.portfolio = portfolio
        self._mock_equity = 10000.0
        self._mock_holdings = {}

    def _get_auth_headers(self, method: str, path: str, body: str = "") -> dict:
        if self.simulation_mode:
            return {"Content-Type": "application/json"}

        timestamp = str(int(time.time()))
        message = timestamp + method.upper() + path + body
        signature = base64.b64encode(
            hmac.new(self.secret_key.encode(), message.encode(), hashlib.sha256).digest()
        ).decode()

        return {
            "CB-ACCESS-KEY": self.api_key,
            "CB-ACCESS-SIGN": signature,
            "CB-ACCESS-TIMESTAMP": timestamp,
            "CB-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }

    async def get(self, path: str) -> dict:
        headers = self._get_auth_headers("GET", path)
        return await super().get(path, headers=headers)

    async def post(self, path: str, body: dict) -> dict:
        body_json = json.dumps(body)
        headers = self._get_auth_headers("POST", path, body_json)
        return await super().post(path, body, headers=headers)

    async def fetch_account_info(self) -> dict:
        """
        Returns account balances. In live mode, calls /accounts.
        In sim mode, returns mock data.
        """
        if self.simulation_mode:
            logging.debug("CryptoAPI: simulation_mode – returning mock account info")
            return {"currency": "USD", "balance": self._mock_equity}

        return await self.get("/accounts")

    async def fetch_holdings(self) -> dict:
        """
        Returns a mapping symbol -> balance.
        """
        if self.simulation_mode:
            logging.debug("CryptoAPI: simulation_mode – returning mock holdings")
            return self._mock_holdings

        accounts = await self.get("/accounts")
        balances = {}
        for acct in accounts:
            cur = acct.get("currency")
            bal = float(acct.get("balance", 0))
            if cur and bal:
                balances[cur] = bal
        return balances

    async def fetch_market_price(self, product_id: str) -> dict:
        """
        Get current bid/ask for a product, e.g., 'BTC-USD'
        """
        if self.simulation_mode:
            logging.debug(f"CryptoAPI: sim price for {product_id}")
            return {"price": 0.0, "bid": 0.0, "ask": 0.0}

        return await self.get(f"/products/{product_id}/ticker")

    async def place_order(
        self,
        product_id: str,
        side: str,
        size: float,
        price: float = None,
        order_type: str = "market",
        **kwargs,
    ) -> dict:
        """
        Places a market or limit order.
        """
        if self.simulation_mode:
            logging.info(f"CryptoAPI: sim {order_type} order {side} {size} {product_id}")
            trade_price = price
            if trade_price is None:
                data = await self.fetch_market_price(product_id)
                trade_price = float(data.get("price", 0))
            if self.portfolio:
                conf = kwargs.get("confidence", 0.0)
                self.portfolio.execute_trade(product_id, side, size, trade_price, conf)
            return {"id": "sim_order", "status": "done", "filled_size": size, "price": trade_price}

        order = {
            "product_id": product_id,
            "side": side,
            "size": str(size),
            "type": order_type,
        }
        if order_type == "limit" and price is not None:
            order["price"] = str(price)
            order.setdefault("time_in_force", "GTC")

        return await self.post("/orders", order)

    async def close(self):
        """Clean up HTTP session."""
        await super().close()
