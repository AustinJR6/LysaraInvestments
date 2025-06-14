from __future__ import annotations

"""Market perception module for Lysara agent."""

from dataclasses import dataclass
from typing import Dict, Any
import logging

from api.crypto_api import CryptoAPI
from data.sentiment import (
    fetch_cryptopanic_sentiment,
    fetch_reddit_sentiment,
)
from utils.helpers import format_timestamp


@dataclass
class MarketSnapshot:
    """Unified view of current market data."""

    prices: Dict[str, float]
    sentiment: Dict[str, Any]
    timestamp: str


async def gather_market_snapshot(config: Dict) -> MarketSnapshot:
    """Collect prices and sentiment into a single snapshot."""

    api_keys = config.get("api_keys", {})
    symbols = config.get("crypto_settings", {}).get("trade_symbols", [])

    prices: Dict[str, float] = {}
    sentiment: Dict[str, Any] = {}

    # ---- Price Data -----------------------------------------------------
    if api_keys.get("coinbase"):
        api = CryptoAPI(
            api_key=api_keys.get("coinbase"),
            secret_key=api_keys.get("coinbase_secret", ""),
            passphrase=api_keys.get("coinbase_passphrase", ""),
            simulation_mode=True,
            config=config,
        )
        for sym in symbols:
            try:
                data = await api.fetch_market_price(sym)
                prices[sym] = float(data.get("price", 0))
            except Exception as e:  # pragma: no cover - network errors
                logging.error(f"Price fetch failed for {sym}: {e}")
                prices[sym] = 0.0
    else:
        logging.debug("Perception: coinbase key missing, skipping price fetch")

    # ---- Sentiment Data -------------------------------------------------
    cp_key = api_keys.get("cryptopanic")
    if cp_key:
        try:
            sentiment["cryptopanic"] = await fetch_cryptopanic_sentiment(cp_key, symbols)
        except Exception as e:  # pragma: no cover - network errors
            logging.error(f"CryptoPanic fetch failed: {e}")
    subreddits = config.get("reddit_subreddits", ["Cryptocurrency"])
    reddit_scores: Dict[str, Any] = {}
    for sub in subreddits:
        try:
            reddit_scores[sub] = await fetch_reddit_sentiment(sub)
        except Exception as e:  # pragma: no cover - network errors
            logging.error(f"Reddit sentiment failed for {sub}: {e}")
    if reddit_scores:
        sentiment["reddit"] = reddit_scores

    return MarketSnapshot(prices=prices, sentiment=sentiment, timestamp=format_timestamp())

