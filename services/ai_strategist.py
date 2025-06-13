import os
import json
import logging
from pathlib import Path
from datetime import datetime
import asyncio

import openai
from dotenv import load_dotenv

# Ensure .env variables are loaded before accessing the API key.  This allows
# modules that import ai_strategist before the main configuration loads the
# environment to still pick up the key.
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

SYSTEM_PROMPT = (
    "You are a trading strategist assistant. Analyze the following context and "
    "return a clear trade recommendation in JSON format."
)

RETURN_INSTRUCTION = "Return JSON: { action, confidence (0-1), reason }"

async def _call_openai(messages: list[dict]) -> str:
    """Call OpenAI ChatCompletion API and return the message content."""
    try:
        resp = await asyncio.to_thread(
            openai.chat.completions.create,
            model="gpt-4o",
            messages=messages,
            temperature=0.2,
        )
        return resp.choices[0].message.content.strip()
    except AttributeError:
        # Fallback for older openai<1.0
        resp = await asyncio.to_thread(
            openai.ChatCompletion.create,
            model="gpt-4o",
            messages=messages,
            temperature=0.2,
        )
        return resp["choices"][0]["message"]["content"].strip()


def _log_decision(context: dict, decision: dict) -> None:
    """Append AI decisions to log file."""
    try:
        Path("logs").mkdir(exist_ok=True)
        log_path = Path("logs/ai_decisions.log")
        line = f"{datetime.utcnow().isoformat()} context={json.dumps(context)} "
        line += f"decision={json.dumps(decision)}\n"
        with open(log_path, "a") as f:
            f.write(line)
    except Exception as e:
        logging.error(f"Failed to log AI decision: {e}")


async def get_ai_trade_decision(context: dict) -> dict:
    """Analyze market context with GPT-3.5 and return a trade decision."""
    enabled = os.getenv("ENABLE_AI_STRATEGY", "true").lower() in ("true", "1", "yes")
    if not enabled:
        return {"action": "hold", "confidence": 0.5, "reason": "AI disabled"}

    if not openai.api_key:
        logging.error("OPENAI_API_KEY not set")
        return {"action": "hold", "confidence": 0.5, "reason": "No API key"}

    user_content = "\n".join(f"{k}: {v}" for k, v in context.items())
    user_content += f"\n\n{RETURN_INSTRUCTION}"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    for attempt in range(3):
        try:
            text = await _call_openai(messages)
            decision = json.loads(text)
            _log_decision(context, decision)
            return decision
        except Exception as e:
            logging.error(f"OpenAI call failed (attempt {attempt+1}): {e}")
            await asyncio.sleep(2)

    return {"action": "hold", "confidence": 0.5, "reason": "AI error"}


def get_last_decision(log_path: str = "logs/ai_decisions.log") -> dict:
    """Return the most recent AI decision and context from log file."""
    path = Path(log_path)
    if not path.is_file():
        return {}
    try:
        lines = path.read_text().strip().splitlines()
        if not lines:
            return {}
        last = lines[-1]
        ts_part, rest = last.split(" ", 1)
        ctx_str = rest.split("context=")[1].split(" decision=")[0]
        dec_str = rest.split("decision=")[1]
        return {
            "timestamp": ts_part,
            "context": json.loads(ctx_str),
            "decision": json.loads(dec_str),
        }
    except Exception as e:
        logging.error(f"Failed to read last AI decision: {e}")
        return {}


async def _fetch_news_headlines(api_key: str, limit: int = 20) -> list[str]:
    """Return a list of recent business/crypto news headlines."""
    import aiohttp

    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "category": "business",
        "language": "en",
        "pageSize": limit,
        "apiKey": api_key,
    }
    headlines: list[str] = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                for art in data.get("articles", []):
                    title = art.get("title")
                    if title:
                        headlines.append(title)
    except Exception as e:
        logging.error(f"NewsAPI fetch failed: {e}")
    return headlines


async def ai_discover_assets(base_symbols: list[str] | None = None) -> list[str]:
    """Return 2-3 trending symbols not already in base_symbols."""
    enabled = os.getenv("ENABLE_AI_ASSET_DISCOVERY", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    if not enabled:
        return []

    if not openai.api_key:
        logging.error("OPENAI_API_KEY not set for asset discovery")
        return []

    base_symbols = base_symbols or []
    news_key = os.getenv("NEWSAPI_KEY")
    headlines: list[str] = []
    if news_key:
        headlines = await _fetch_news_headlines(news_key, limit=20)

    user_msg = (
        "Existing symbols: "
        + ",".join(base_symbols)
        + "\nRecent headlines:\n"
        + "\n".join(headlines[:20])
        + "\nSuggest up to 3 additional liquid trading symbols not already in the list."
        " Return JSON: { symbols: [symbol,...], reason }"
    )

    messages = [
        {
            "role": "system",
            "content": "You are a market analyst recommending assets.",
        },
        {"role": "user", "content": user_msg},
    ]

    try:
        text = await _call_openai(messages)
        data = json.loads(text)
        symbols = [s.strip().upper() for s in data.get("symbols", [])]
        reason = data.get("reason", "")
        symbols = [s for s in symbols if s and s not in base_symbols]
        if symbols:
            logging.info(f"[AI_DISCOVERED] {symbols} reason={reason}")
        return symbols
    except Exception as e:
        logging.error(f"AI asset discovery failed: {e}")
        return []
