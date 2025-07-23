# data/market_data_alpaca.py
"""Real-time stock market data streaming via Alpaca's websocket API."""

import asyncio
import json
import logging

import websockets


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
            "symbol": bar["symbol"],
            "price": float(bar["close"]),
            "time": bar.get("timestamp", ""),
        }
        if on_bar:
            await on_bar(data)
        else:
            logging.info(f"[ALPACA WS] {data['symbol']} @ {data['price']}")

    url = f"wss://stream.data.alpaca.markets/v2/{data_feed}"
    logging.info(
        f"Connecting to Alpaca WS feed {url} for symbols: {', '.join(symbols)}"
    )

    while True:
        try:
            async with websockets.connect(url) as ws:
                auth = {"action": "auth", "key": api_key, "secret": api_secret}
                await ws.send(json.dumps(auth))
                subs = {"action": "subscribe", "bars": symbols}
                await ws.send(json.dumps(subs))

                async for msg in ws:
                    logging.debug(f"Alpaca WS raw: {msg}")
                    data = json.loads(msg)
                    for bar in data.get("bars", []):
                        parsed = {
                            "symbol": bar.get("S"),
                            "close": bar.get("c"),
                            "timestamp": bar.get("t"),
                        }
                        await handle_bar(parsed)
        except Exception as e:
            logging.error(f"Alpaca WS error: {e}")
            await asyncio.sleep(5)

