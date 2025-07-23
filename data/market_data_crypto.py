# data/market_data_crypto.py

import asyncio
import websockets
import json
import logging
from datetime import datetime

# This module is configured to use Binance.US endpoints

# Default subscription message if no symbols provided.
SUBSCRIBE_MESSAGE = {
    "method": "SUBSCRIBE",
    "params": ["btcusdt@ticker", "ethusdt@ticker"],
    "id": 1,
}

# Replace this with a more robust handler in your strategy later
async def handle_market_message(message: dict):
    logging.info(f"[CRYPTO WS] Ticker update: {message.get('symbol')} @ {message.get('price')}")


async def start_crypto_market_feed(symbols: list[str], on_message=handle_market_message):
    """Launch a Binance WebSocket connection for real-time ticker data."""
    # Coinbase WebSocket does not provide unique sentiment streams, so we use
    # Binance for market data and trading. Coinbase support has been removed.
    # Connect to Binance.US WebSocket endpoint
    uri = "wss://stream.binance.us:9443/stream"
    stream = "/".join([f"{s.lower().replace('-', '')}@ticker" for s in symbols])
    subscribe_msg = {
        "method": "SUBSCRIBE",
        "params": [f"{s.lower().replace('-', '')}@ticker" for s in symbols],
        "id": 1,
    }

    while True:
        try:
            async with websockets.connect(uri) as ws:
                await ws.send(json.dumps(subscribe_msg))
                logging.info("Connected to Binance WebSocket feed.")
                async for raw_msg in ws:
                    msg = json.loads(raw_msg)
                    data = msg.get("data", {})
                    if data.get("e") == "24hrTicker":
                        await on_message({
                            "symbol": data.get("s"),
                            "price": data.get("c"),
                            "timestamp": datetime.utcnow().isoformat(),
                        })
        except Exception as e:
            logging.error(f"WebSocket error: {e}")
            logging.info("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
