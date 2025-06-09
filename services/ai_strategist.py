import os
import json
import logging
from pathlib import Path
from datetime import datetime
import asyncio

import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

SYSTEM_PROMPT = (
    "You are a trading strategist assistant. Analyze the following context and "
    "return a clear trade recommendation in JSON format."
)

RETURN_INSTRUCTION = "Return JSON: { action, confidence (0-1), reason }"

async def _call_openai(messages: list[dict]) -> str:
    """Call OpenAI ChatCompletion API and return the message content."""
    resp = await asyncio.to_thread(
        openai.ChatCompletion.create,
        model="gpt-3.5-turbo",
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
