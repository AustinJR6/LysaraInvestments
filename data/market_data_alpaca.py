# data/market_data_alpaca.py
"""Real-time stock market data streaming via Alpaca's websocket API."""

import asyncio
import logging
from alpaca_trade_api.stream import Stream


async def start_stock_ws_feed(
    symbols: list[str],
    api_key: str,
    api_secret: str,
    base_url: str,
    data_feed: str = "iex",
    on_bar=None,
):
    """Run a websocket loop streaming live bars from Alpaca."""

    async def handle_bar(bar):
        data = {
            "symbol": bar.symbol,
            "price": float(bar.close),
            "time": bar.timestamp.isoformat(),
        }
        if on_bar:
            await on_bar(data)
        else:
            logging.info(f"[ALPACA WS] {data['symbol']} @ {data['price']}")

    while True:
        stream = Stream(api_key, api_secret, base_url=base_url, data_feed=data_feed)

        for sym in symbols:
            stream.subscribe_bars(handle_bar, sym)

        try:
            await stream._run_forever()
        except Exception as e:
            logging.error(f"Alpaca WS error: {e}")
            await asyncio.sleep(5)
            continue

