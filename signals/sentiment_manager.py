import json
from pathlib import Path

SENTIMENT_PATH = Path("dashboard/data/sentiment_cache.json")


def get_sentiment_score(symbol: str) -> float:
    """Return sentiment score for a symbol from cache, or 0.0 if unavailable."""
    if not SENTIMENT_PATH.is_file():
        return 0.0
    try:
        data = json.loads(SENTIMENT_PATH.read_text())
        return data.get("cryptopanic", {}).get(symbol, {}).get("score", 0.0)
    except Exception:
        return 0.0
