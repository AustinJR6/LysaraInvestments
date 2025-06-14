"""Persistent memory store for agent decisions and trades."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import logging

from db.db_manager import DatabaseManager


class AgentMemory:
    """Log and recall decisions and trade results."""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.log_path = Path("logs/agent_decisions.log")
        self.log_path.parent.mkdir(exist_ok=True)

    def log_decision(self, decision: Dict[str, Any], context: Dict[str, Any]):
        line = f"{datetime.utcnow().isoformat()} context={json.dumps(context)} decision={json.dumps(decision)}\n"
        try:
            with open(self.log_path, "a") as f:
                f.write(line)
        except Exception as e:
            logging.error(f"Failed to log decision: {e}")

    def log_trade(self, **kwargs):
        try:
            self.db.log_trade(**kwargs)
        except Exception as e:
            logging.error(f"Failed to log trade: {e}")

    def last_decision(self) -> Dict[str, Any]:
        if not self.log_path.is_file():
            return {}
        try:
            lines = self.log_path.read_text().strip().splitlines()
            if not lines:
                return {}
            ts, rest = lines[-1].split(" ", 1)
            ctx = rest.split("context=")[1].split(" decision=")[0]
            dec = rest.split("decision=")[1]
            return {
                "timestamp": ts,
                "context": json.loads(ctx),
                "decision": json.loads(dec),
            }
        except Exception:
            return {}

