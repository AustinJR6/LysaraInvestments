from __future__ import annotations

"""Market perception module for Lysara agent."""

from typing import Dict, Any
import logging
from datetime import datetime

from api.crypto_api import CryptoAPI
from data.sentiment import (
    fetch_cryptopanic_sentiment,
    fetch_reddit_sentiment,
)
from .market_snapshot import MarketSnapshot


async def gather_market_snapshot(config: Dict, symbol: str) -> MarketSnapshot:
    """Collect prices and sentiment for a single symbol."""

    api_keys = config.get("api_keys", {})
    sentiment: Dict[str, Any] = {}
    price: float = 0.0

    # ---- Price Data -----------------------------------------------------
    if api_keys.get("coinbase"):
        api = CryptoAPI(
            api_key=api_keys.get("coinbase"),
            secret_key=api_keys.get("coinbase_secret", ""),
            simulation_mode=True,
            config=config,
        )
        try:
            data = await api.fetch_market_price(symbol)
            price = float(data.get("price", 0))
        except Exception as e:  # pragma: no cover - network errors
            logging.error(f"Price fetch failed for {symbol}: {e}")
    else:
        logging.debug("Perception: coinbase key missing, skipping price fetch")

    # ---- Sentiment Data -------------------------------------------------
    cp_key = api_keys.get("cryptopanic")
    if cp_key:
        try:
            sentiment["cryptopanic"] = await fetch_cryptopanic_sentiment(cp_key, [symbol])
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

    return MarketSnapshot(
        ticker=symbol,
        price=price,
        sentiment=sentiment,
        technicals={},
        volatility=0.0,
        timestamp=datetime.utcnow(),
    )

