# data/market_data_crypto.py

import asyncio
import websockets
import json
import logging
from datetime import datetime

SUBSCRIBE_MESSAGE = {
    "type": "subscribe",
    "product_ids": ["BTC-USD", "ETH-USD"],
    "channels": ["ticker"]
}

# Replace this with a more robust handler in your strategy later
async def handle_market_message(message: dict):
    logging.info(f"[CRYPTO WS] Ticker update: {message.get('product_id')} @ {message.get('price')}")


async def start_crypto_market_feed(symbols: list[str], on_message=handle_market_message):
    """
    Launches a Coinbase WebSocket connection for real-time ticker data.
    """
    uri = "wss://advanced-trade-ws.coinbase.com"
    subscribe_msg = {
        "type": "subscribe",
        "product_ids": symbols,
        "channels": ["ticker"]
    }

    while True:
        try:
            async with websockets.connect(uri) as ws:
                await ws.send(json.dumps(subscribe_msg))
                logging.info("Connected to Coinbase WebSocket feed.")
                async for raw_msg in ws:
                    msg = json.loads(raw_msg)
                    if msg.get("type") == "ticker":
                        await on_message(msg)
        except Exception as e:
            logging.error(f"WebSocket error: {e}")
            logging.info("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
