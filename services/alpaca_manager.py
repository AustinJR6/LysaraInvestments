import asyncio
import logging
import os
from typing import Optional

from dotenv import load_dotenv

from utils.guardrails import log_live_trade
from alpaca_client import (
    get_account,
    get_positions,
    place_order as api_place_order,
    fetch_market_price,
)

load_dotenv()


class AlpacaManager:
    """Thin wrapper around Alpaca REST API using `requests`."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://paper-api.alpaca.markets",
        simulation_mode: bool = True,
        portfolio=None,
        config: Optional[dict] = None,
        trade_cooldown: int = 30,
    ) -> None:
        self.simulation_mode = simulation_mode
        self.portfolio = portfolio
        self.config = config or {}
        self.trade_cooldown = trade_cooldown
        self._last_trade: dict[str, float] = {}

        # ensure credentials are available to alpaca_client
        os.environ.setdefault("ALPACA_API_KEY", api_key)
        os.environ.setdefault("ALPACA_SECRET_KEY", api_secret)
        os.environ.setdefault("ALPACA_BASE_URL", base_url)

    async def get_account(self):
        if self.simulation_mode:
            logging.debug("AlpacaManager: returning mock account data")
            return {"cash": 10000.0, "equity": 10000.0, "buying_power": 10000.0}
        return await get_account()

    async def get_positions(self):
        if self.simulation_mode:
            logging.debug("AlpacaManager: returning empty positions in sim mode")
            return []
        return await get_positions()

    async def fetch_market_price(self, symbol: str) -> dict:
        return await fetch_market_price(symbol)

    async def place_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        type: str = "market",
        time_in_force: str = "day",
        price: float | None = None,
        **kwargs,
    ):
        if self.simulation_mode:
            logging.info(f"[SIM] {side.upper()} {qty} {symbol}")
            if self.portfolio:
                if price is None:
                    price = (await self.fetch_market_price(symbol)).get("price", 0)
                self.portfolio.execute_trade(symbol, side, qty, price)
            return {"id": "sim", "status": "filled", "symbol": symbol, "qty": qty, "price": price}

        now = asyncio.get_event_loop().time()
        last = self._last_trade.get(symbol)
        if last and now - last < self.trade_cooldown:
            logging.warning(f"Duplicate trade blocked for {symbol}")
            return {"status": "blocked", "reason": "duplicate"}
        self._last_trade[symbol] = now

        order = await api_place_order(
            symbol=symbol,
            side=side,
            qty=qty,
            type=type,
            time_in_force=time_in_force,
        )
        trade_price = price if price is not None else (
            await self.fetch_market_price(symbol)
        ).get("price", 0)
        await log_live_trade(
            symbol,
            side,
            qty,
            trade_price,
            self.config,
            market="stock",
            confidence=kwargs.get("confidence"),
            risk_pct=self.config.get("stocks_settings", {}).get("risk_per_trade") * 100 if self.config.get("stocks_settings") else None,
        )
        return order

