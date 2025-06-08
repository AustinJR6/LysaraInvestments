# services/background_tasks.py

import asyncio
import logging
from data.sentiment import fetch_cryptopanic_sentiment, fetch_newsapi_sentiment

class BackgroundTasks:
    def __init__(self, config: dict):
        self.config = config
        self.crypto_symbols = config.get("TRADE_SYMBOLS", ["BTC-USD", "ETH-USD"])
        self.cp_key = config["api_keys"].get("cryptopanic")
        self.newsapi_key = config["api_keys"].get("newsapi")
        self._running = True

    async def run_sentiment_loop(self, interval: int = 60):
        """
        Loop fetching sentiment scores at defined intervals.
        """
        while self._running:
            logging.info("Running sentiment fetch loop...")

            if self.cp_key:
                scores = await fetch_cryptopanic_sentiment(self.cp_key, self.crypto_symbols)
                logging.info(f"CryptoPanic Sentiment: {scores}")

            if self.newsapi_key:
                news = await fetch_newsapi_sentiment(self.newsapi_key)
                logging.info(f"NewsAPI Sentiment: {news}")

            await asyncio.sleep(interval)

    async def run_dummy_task(self, label: str = "heartbeat", interval: int = 10):
        """
        Simple repeating log task for dev/testing.
        """
        while self._running:
            logging.info(f"[{label}] heartbeat alive")
            await asyncio.sleep(interval)

    def stop(self):
        self._running = False
