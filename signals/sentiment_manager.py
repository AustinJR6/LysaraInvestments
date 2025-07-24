import json
from pathlib import Path

SENTIMENT_PATH = Path("dashboard/data/sentiment_cache.json")


def get_sentiment_score(symbol: str) -> float:
    """Return sentiment score for a symbol from cache, or 0.0 if unavailable."""
    if not SENTIMENT_PATH.is_file():
        return 0.0
    try:
        data = json.loads(SENTIMENT_PATH.read_text())
        scores = []

        reddit_data = data.get("reddit", {})
        if isinstance(reddit_data, dict):
            for entry in reddit_data.values():
                val = entry.get("score")
                if val is not None:
                    scores.append(float(val))

        news_score = data.get("newsapi", {}).get("score")
        if news_score is not None:
            scores.append(float(news_score))

        return sum(scores) / len(scores) if scores else 0.0
    except Exception:
        return 0.0
