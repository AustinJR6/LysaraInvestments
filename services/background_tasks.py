# services/background_tasks.py

import asyncio
import logging
import json
from pathlib import Path

from data.sentiment import (
    fetch_cryptopanic_sentiment,
    fetch_newsapi_sentiment,
    fetch_reddit_sentiment,
)

class BackgroundTasks:
    def __init__(self, config: dict):
        self.config = config
        self.crypto_symbols = config.get("TRADE_SYMBOLS", ["BTC-USD", "ETH-USD"])
        self.cp_key = config["api_keys"].get("cryptopanic")
        self.newsapi_key = config["api_keys"].get("newsapi")
        self.subreddits = config.get("reddit_subreddits", ["Cryptocurrency"])
        self.sentiment_scores: dict = {}
        self._running = True

        self.sentiment_file = Path("dashboard/data/sentiment_cache.json")

    def _persist_scores(self):
        try:
            self.sentiment_file.parent.mkdir(parents=True, exist_ok=True)
            self.sentiment_file.write_text(json.dumps(self.sentiment_scores, indent=2))
        except Exception as e:
            logging.error(f"Failed to persist sentiment scores: {e}")

    async def run_sentiment_loop(self, interval: int = 60):
        """
        Loop fetching sentiment scores at defined intervals.
        """
        while self._running:
            logging.info("Running sentiment fetch loop...")

            if self.cp_key:
                scores = await fetch_cryptopanic_sentiment(self.cp_key, self.crypto_symbols)
                self.sentiment_scores["cryptopanic"] = scores
                logging.info(f"CryptoPanic Sentiment: {scores}")

            if self.newsapi_key:
                news = await fetch_newsapi_sentiment(self.newsapi_key)
                self.sentiment_scores["newsapi"] = news
                logging.info(f"NewsAPI Sentiment: {news}")

            if self.subreddits:
                reddit_scores = {}
                for sub in self.subreddits:
                    reddit_scores[sub] = await fetch_reddit_sentiment(sub)
                self.sentiment_scores["reddit"] = reddit_scores
                logging.info(f"Reddit Sentiment: {reddit_scores}")

            self._persist_scores()
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
