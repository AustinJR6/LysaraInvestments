import os
import time
import json
import logging
import asyncio
from typing import Dict, Any

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY", "")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
PAPER_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
LIVE_URL = os.getenv("ALPACA_LIVE_URL", "https://api.alpaca.markets")


def _headers() -> Dict[str, str]:
    return {
        "APCA-API-KEY-ID": API_KEY,
        "APCA-API-SECRET-KEY": SECRET_KEY,
    }


def _request(method: str, path: str, *, live: bool = False, **kwargs) -> Dict[str, Any]:
    base_url = LIVE_URL if live else PAPER_URL
    url = f"{base_url.rstrip('/')}{path}"
    for attempt in range(1, 4):
        try:
            resp = requests.request(method, url, headers=_headers(), timeout=10, **kwargs)
            resp.raise_for_status()
            if resp.text:
                return resp.json()
            return {}
        except Exception as e:
            logging.error(f"{method} {url} failed (attempt {attempt}): {e}")
            time.sleep(2 ** (attempt - 1))
    return {}


async def get_account(live: bool = False) -> Dict[str, Any]:
    return await asyncio.to_thread(_request, "GET", "/v2/account", live=live)


async def get_positions(live: bool = False) -> Any:
    return await asyncio.to_thread(_request, "GET", "/v2/positions", live=live)


async def place_order(
    symbol: str,
    side: str,
    qty: float,
    type: str = "market",
    time_in_force: str = "gtc",
    live: bool = False,
) -> Dict[str, Any]:
    body = {
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "type": type,
        "time_in_force": time_in_force,
    }
    return await asyncio.to_thread(
        _request, "POST", "/v2/orders", json=body, live=live
    )


async def cancel_order(order_id: str, live: bool = False) -> Dict[str, Any]:
    path = f"/v2/orders/{order_id}"
    return await asyncio.to_thread(_request, "DELETE", path, live=live)


async def fetch_market_price(symbol: str, live: bool = False) -> Dict[str, Any]:
    path = f"/v2/stocks/{symbol}/trades/latest"
    data = await asyncio.to_thread(_request, "GET", path, live=live)
    price = 0.0
    if isinstance(data, dict):
        price = float(data.get("trade", {}).get("p", 0))
    return {"price": price}
