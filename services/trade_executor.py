"""Wrapper around BotLauncher for agent use."""

from __future__ import annotations

from typing import Dict

from services.bot_launcher import BotLauncher


class TradeExecutorService:
    """Provide start/stop hooks for trading bots."""

    def __init__(self, config: Dict):
        self.launcher = BotLauncher(config)

    def start(self):
        self.launcher.start_all_bots()

    # TODO: expand with pause/stop logic

