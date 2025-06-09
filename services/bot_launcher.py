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
from services.sim_portfolio import SimulatedPortfolio


class BotLauncher:
    def __init__(self, config: dict):
        self.config = config
        self.db = DatabaseManager(config.get("db_path", "trades.db"))
        self.bg_tasks = BackgroundTasks(config)
        self.sim_portfolio = None
        if self.config.get("simulation_mode", True):
            starting = self.config.get("starting_balance", 1000.0)
            state_file = self.config.get("sim_state_file", "data/sim_state.json")
            self.sim_portfolio = SimulatedPortfolio(starting_balance=starting, state_file=state_file)

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
            simulation_mode=self.config.get("simulation_mode", True),
            portfolio=self.sim_portfolio,
            config=self.config,
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
        logging.info("Starting stock bots...")

        api_keys = self.config.get("api_keys", {})
        settings = self.config.get("stocks_settings", {})
        symbols = settings.get("trade_symbols", ["AAPL", "TSLA"])

        stock_key = api_keys.get("robinhood") or api_keys.get("alphavantage")
        if not stock_key:
            logging.error("Stock API key missing or invalid. Bots disabled.")
            return

        stock_api = StockAPI(
            api_key=stock_key,
            api_secret=api_keys.get("robinhood_secret"),
            simulation_mode=self.config.get("simulation_mode", True),
            portfolio=self.sim_portfolio,
        )

        await stock_api.fetch_account_info()

        risk = RiskManager(stock_api, settings)
        await risk.update_equity()

        from strategies.stocks.stock_momentum import StockMomentumStrategy

        strategy = StockMomentumStrategy(
            api=stock_api,
            risk=risk,
            config=settings,
            db=self.db,
            symbol_list=symbols,
        )

        from data.market_data_stocks import start_stock_polling_loop

        asyncio.create_task(start_stock_polling_loop(symbols, stock_key))
        asyncio.create_task(strategy.run())

    async def start_forex_bots(self):
        logging.info("Starting forex bots...")

        api_keys = self.config.get("api_keys", {})
        settings = self.config.get("forex_settings", {})
        instruments = settings.get("trade_symbols", ["EUR_USD", "GBP_USD"])

        api_key = api_keys.get("oanda")
        account_id = api_keys.get("oanda_account_id")
        if not api_key or not account_id:
            logging.error("OANDA API credentials missing or invalid. Bots disabled.")
            return

        forex_api = ForexAPI(
            api_key=api_key,
            account_id=account_id,
            simulation_mode=self.config.get("simulation_mode", True),
            portfolio=self.sim_portfolio,
        )

        await forex_api.get_account_info()

        risk = RiskManager(forex_api, settings)
        await risk.update_equity()

        from strategies.forex.rsi_trend import ForexRSITrendStrategy

        strategy = ForexRSITrendStrategy(
            api=forex_api,
            risk=risk,
            config=settings,
            db=self.db,
            symbol_list=instruments,
        )

        from data.market_data_forex import start_forex_polling_loop

        asyncio.create_task(start_forex_polling_loop(instruments, api_key, account_id))
        asyncio.create_task(strategy.run())
