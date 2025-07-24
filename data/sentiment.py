# data/sentiment.py

import aiohttp
import logging
from textblob import TextBlob
from datetime import datetime

# === Helper ===

def analyze_sentiment(text: str) -> float:
    """
    Returns a polarity score between -1.0 (negative) and 1.0 (positive).
    """
    try:
        return TextBlob(text).sentiment.polarity
    except Exception as e:
        logging.warning(f"Sentiment analysis failed: {e}")
        return 0.0

# === CryptoPanic ===

# The CryptoPanic API integration has been removed.
# The original function has been commented out to disable requests.

# async def fetch_cryptopanic_sentiment(api_key: str, symbols: list[str]) -> dict:
#     """Pulls latest sentiment data for crypto from CryptoPanic API."""
#     url = "https://cryptopanic.com/api/v1/posts/"
#     headers = {"Accept": "application/json"}
#     result = {}
#     async with aiohttp.ClientSession() as session:
#         for symbol in symbols:
#             params = {
#                 "auth_token": api_key,
#                 "currencies": symbol.split("-")[0].lower(),
#                 "filter": "rising",
#                 "public": "true"
#             }
#             try:
#                 async with session.get(url, params=params, headers=headers) as response:
#                     data = await response.json()
#                     posts = data.get("results", [])
#                     scores = [
#                         analyze_sentiment(
#                             (p.get("title") or "") + " " + (p.get("body") or "")
#                         )
#                         for p in posts
#                     ]
#                     avg_score = round(sum(scores) / len(scores), 3) if scores else 0.0
#                     result[symbol] = {
#                         "score": avg_score,
#                         "count": len(scores),
#                         "timestamp": datetime.utcnow().isoformat()
#                     }
#             except Exception as e:
#                 logging.error(f"CryptoPanic error for {symbol}: {e}")
#                 result[symbol] = {"score": 0.0, "count": 0}
#     return result

# === NewsAPI ===

async def fetch_newsapi_sentiment(api_key: str, query: str = "Bitcoin") -> dict:
    """
    Fetches recent headlines from NewsAPI and performs sentiment analysis.
    """
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "sortBy": "publishedAt",
        "language": "en",
        "apiKey": api_key
    }
    scores = []

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                articles = data.get("articles", [])
                for article in articles:
                    title = article.get("title") or ""
                    desc = article.get("description") or ""
                    content = title + " " + desc
                    scores.append(analyze_sentiment(content))
    except Exception as e:
        logging.error(f"NewsAPI error: {e}")

    return {
        "score": round(sum(scores) / len(scores), 3) if scores else 0.0,
        "count": len(scores),
        "timestamp": datetime.utcnow().isoformat()
    }

# === Reddit ===

async def fetch_reddit_sentiment(subreddit: str, limit: int = 50) -> dict:
    """Gather sentiment score from a subreddit."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    headers = {"User-Agent": "LysaraBot/0.1"}
    scores = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                data = await response.json()
                posts = data.get("data", {}).get("children", [])
                for post in posts:
                    text = post.get("data", {}).get("title", "") + " " + post.get("data", {}).get("selftext", "")
                    scores.append(analyze_sentiment(text))
    except Exception as e:
        logging.error(f"Reddit sentiment error: {e}")
    return {
        "score": round(sum(scores) / len(scores), 3) if scores else 0.0,
        "count": len(scores),
        "timestamp": datetime.utcnow().isoformat(),
    }
