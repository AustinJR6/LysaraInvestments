# data/market_data_coingecko.py
"""Fetch current cryptocurrency prices from the public CoinGecko API."""

import asyncio
import logging
from datetime import datetime

import aiohttp

from .price_cache import get_price, update_price


async def fetch_coingecko_price(session: aiohttp.ClientSession, coin_id: str) -> dict:
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": coin_id, "vs_currencies": "usd"}
    try:
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            price = data.get(coin_id, {}).get("usd", 0.0)
            if price:
                update_price(f"{coin_id.upper()}-USD", price, "coingecko")
            else:
                logging.debug(f"CoinGecko returned zero price for {coin_id}")
            return {
                "symbol": coin_id,
                "price": price,
                "time": datetime.utcnow().isoformat(),
            }
    except Exception as e:
        logging.error(f"Coingecko price fetch failed: {e}")
        return {"symbol": coin_id, "price": 0.0, "time": datetime.utcnow().isoformat()}


async def start_coingecko_polling(symbols: list[str], interval: int = 60, on_data=None):
    """Poll CoinGecko every ``interval`` seconds for crypto symbols.

    Stock tickers are ignored. Prices already provided by Binance take
    precedence over CoinGecko data.
    """
    coin_ids = []
    for s in symbols:
        if "-" not in s:
            logging.debug(f"Skipping non-crypto symbol {s} for CoinGecko polling")
            continue
        coin_ids.append(s.split("-")[0].lower())
    async with aiohttp.ClientSession() as session:
        while True:
            for cid in coin_ids:
                canonical = f"{cid.upper()}-USD"
                cached = get_price(canonical)
                if cached and cached.get("source") in {"binance", "alpaca"}:
                    continue  # prefer exchange price
                data = await fetch_coingecko_price(session, cid)
                if on_data:
                    await on_data(data)
                else:
                    logging.info(f"[COINGECKO] {cid} @ {data['price']}")
            await asyncio.sleep(interval)

