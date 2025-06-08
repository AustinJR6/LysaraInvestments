# data/market_data_stocks.py

import asyncio
import aiohttp
import logging
from datetime import datetime

async def fetch_stock_prices(session, symbols: list[str], api_key: str):
    """
    Fetch latest stock prices from a public or Alpaca endpoint.
    Replace with a real-time feed later if needed.
    """
    url = f"https://api.twelvedata.com/price"
    results = []

    for symbol in symbols:
        params = {
            "symbol": symbol,
            "apikey": api_key
        }
        try:
            async with session.get(url, params=params) as response:
                data = await response.json()
                results.append({
                    "symbol": symbol,
                    "price": float(data.get("price", 0)),
                    "time": datetime.utcnow().isoformat()
                })
        except Exception as e:
            logging.error(f"Failed to fetch price for {symbol}: {e}")

    return results

async def start_stock_polling_loop(symbols, api_key, interval=10, on_price=None):
    """
    Polls stock prices every `interval` seconds using TwelveData or similar.
    """
    async with aiohttp.ClientSession() as session:
        while True:
            prices = await fetch_stock_prices(session, symbols, api_key)
            for p in prices:
                if on_price:
                    await on_price(p)
            await asyncio.sleep(interval)
