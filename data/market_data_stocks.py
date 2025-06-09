# data/market_data_stocks.py

import asyncio
import logging
from datetime import datetime

from services.alpaca_manager import AlpacaManager


async def fetch_stock_prices(alpaca: AlpacaManager, symbols: list[str]):
    """Fetch latest stock prices using Alpaca market data."""
    results = []
    for symbol in symbols:
        try:
            price = (await alpaca.fetch_market_price(symbol)).get("price", 0)
            results.append({
                "symbol": symbol,
                "price": price,
                "time": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logging.error(f"Failed to fetch price for {symbol}: {e}")
    return results


async def start_stock_polling_loop(symbols, alpaca: AlpacaManager, interval=10, on_price=None):
    """Poll stock prices every `interval` seconds via Alpaca."""
    while True:
        prices = await fetch_stock_prices(alpaca, symbols)
        for p in prices:
            if on_price:
                await on_price(p)
        await asyncio.sleep(interval)
