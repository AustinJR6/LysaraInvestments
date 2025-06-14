"""Main loop orchestrating perception, decision and execution."""

from __future__ import annotations

import asyncio
import logging
from typing import Dict

from .perception import gather_market_snapshot
from .decision_engine import make_trade_decision
from .executor import TradeExecutor
from .memory import AgentMemory
from .safety import SafetyMonitor
from db.db_manager import DatabaseManager


class AgentLoop:
    def __init__(self, config: Dict):
        self.config = config
        self.interval = config.get("trade_interval_minutes", 15)
        self.db = DatabaseManager(config.get("db_path", "trades.db"))
        self.memory = AgentMemory(self.db)
        self.executor = TradeExecutor(config)
        self.safety = SafetyMonitor(self.db, config)
        self.symbol = config.get("crypto_settings", {}).get("trade_symbols", ["BTC-USD"])[0]

    async def step(self):
        snapshot = await gather_market_snapshot(self.config)
        decision = make_trade_decision(snapshot, self.config)
        self.memory.log_decision(decision, {"prices": snapshot.prices})
        if self.safety.check():
            await self.executor.execute(decision, self.symbol)
        else:
            logging.warning("Agent disabled by safety monitor")

    async def run(self):
        while True:
            await self.step()
            await asyncio.sleep(self.interval * 60)

