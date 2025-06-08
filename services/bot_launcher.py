# services/bot_launcher.py

import asyncio
import logging

from api.crypto_api import CryptoAPI
from api.stock_api import StockAPI
from api.forex_api import ForexAPI
from risk.risk_manager import RiskManager
from strategies.crypto.momentum import MomentumStrategy
from data.market_data_crypto import start_crypto_market_feed
from db.db_manager import DatabaseManager
from services.background_tasks import BackgroundTasks


class BotLauncher:
    def __init__(self, config: dict):
        self.config = config
        self.db = DatabaseManager(config.get("db_path", "trades.db"))
        self.bg_tasks = BackgroundTasks(config)

    def start_all_bots(self):
        asyncio.create_task(self.bg_tasks.run_sentiment_loop())

        if self.config.get("ENABLE_CRYPTO_TRADING", True):
            asyncio.create_task(self.start_crypto_bots())

        if self.config.get("ENABLE_STOCK_TRADING", False):
            asyncio.create_task(self.start_stock_bots())

        if self.config.get("ENABLE_FOREX_TRADING", False):
            asyncio.create_task(self.start_forex_bots())

    async def start_crypto_bots(self):
        logging.info(" Starting crypto bots...")

        api_keys = self.config["api_keys"]
        settings = self.config.get("crypto_settings", {})
        symbols = settings.get("trade_symbols", ["BTC-USD", "ETH-USD"])

        crypto_api = CryptoAPI(
            api_key=api_keys["coinbase"],
            secret_key=api_keys["coinbase_secret"],
            simulation_mode=self.config.get("simulation_mode", True)
        )

        await crypto_api.fetch_account_info()

        risk = RiskManager(crypto_api, settings)
        await risk.update_equity()

        strategy = MomentumStrategy(
            api=crypto_api,
            risk=risk,
            config=settings,
            db=self.db,
            symbol_list=symbols,
            sentiment_source=self.bg_tasks,
        )

        asyncio.create_task(start_crypto_market_feed(symbols))
        asyncio.create_task(strategy.run())

    async def start_stock_bots(self):
        logging.info(" Stock bot placeholder started.")
        # Fill in with real strategy and feed integration later

    async def start_forex_bots(self):
        logging.info(" Forex bot placeholder started.")
        # Fill in with real strategy and feed integration later
