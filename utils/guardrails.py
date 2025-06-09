import sys
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
import asyncio
from .notifications import send_slack_message

async def log_live_trade(symbol: str, side: str, qty: float, price: float, config: dict):
    """Append live trade details to log file and optional sqlite db."""
    log_line = f"{datetime.utcnow().isoformat()} {symbol} {side} {qty} @ {price}"
    Path("logs").mkdir(exist_ok=True)
    with open("logs/trade_log.txt", "a") as f:
        f.write(log_line + "\n")

    db_path = Path("data/trade_logs.db")
    try:
        db_path.parent.mkdir(exist_ok=True)
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                side TEXT,
                quantity REAL,
                price REAL
            )"""
        )
        cur.execute(
            "INSERT INTO trades(timestamp, symbol, side, quantity, price) VALUES(?,?,?,?,?)",
            (datetime.utcnow().isoformat(), symbol, side, qty, price)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Trade DB log failed: {e}")

    webhook = config.get("api_keys", {}).get("slack_webhook")
    if webhook:
        await send_slack_message(webhook, log_line)


def confirm_live_mode(simulation_mode: bool):
    """Prompt user before starting live trading."""
    if not simulation_mode:
        resp = input("[!] SIMULATION_MODE is OFF. Proceed with live trading? (y/N) ")
        if resp.strip().lower() != "y":
            print("Aborting launch.")
            sys.exit(0)

