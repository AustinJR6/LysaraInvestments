# data/market_data_coingecko.py
"""Fetch current cryptocurrency prices from the public CoinGecko API."""

import asyncio
import logging
from datetime import datetime

import aiohttp


async def fetch_coingecko_price(session: aiohttp.ClientSession, coin_id: str) -> dict:
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": coin_id, "vs_currencies": "usd"}
    try:
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            price = data.get(coin_id, {}).get("usd", 0.0)
            return {
                "symbol": coin_id,
                "price": price,
                "time": datetime.utcnow().isoformat(),
            }
    except Exception as e:
        logging.error(f"Coingecko price fetch failed: {e}")
        return {"symbol": coin_id, "price": 0.0, "time": datetime.utcnow().isoformat()}


async def start_coingecko_polling(symbols: list[str], interval: int = 60, on_data=None):
    """Poll CoinGecko every `interval` seconds for given symbols."""
    coin_ids = [s.split("-")[0].lower() for s in symbols]
    async with aiohttp.ClientSession() as session:
        while True:
            for cid in coin_ids:
                data = await fetch_coingecko_price(session, cid)
                if on_data:
                    await on_data(data)
                else:
                    logging.info(f"[COINGECKO] {cid} @ {data['price']}")
            await asyncio.sleep(interval)

