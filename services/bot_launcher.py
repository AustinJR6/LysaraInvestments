# services/bot_launcher.py

import asyncio
import logging
import os

from api.crypto_api import CryptoAPI
from api.forex_api import ForexAPI
from risk.risk_manager import RiskManager
from strategies.crypto.momentum import MomentumStrategy
from data.market_data_crypto import start_crypto_market_feed
from data.market_data_coingecko import start_coingecko_polling
from data.market_data_alpaca import start_stock_ws_feed
from db.db_manager import DatabaseManager
from services.background_tasks import BackgroundTasks
from services.sim_portfolio import SimulatedPortfolio
from services.heartbeat import heartbeat


class BotLauncher:
    def __init__(self, config: dict):
        self.config = config
        env_syms = os.getenv("TRADE_SYMBOLS", "")
        if env_syms:
            syms = [s.strip().upper() for s in env_syms.split(";") if s.strip()] if ";" in env_syms else [s.strip().upper() for s in env_syms.split(",") if s.strip()]
            crypto = [s for s in syms if "-" in s]
            stocks = [s for s in syms if "-" not in s]
            if crypto:
                self.config["TRADE_SYMBOLS"] = crypto
            if stocks:
                self.config.setdefault("stocks_settings", {}).setdefault(
                    "trade_symbols", stocks
                )
        self.db = DatabaseManager(config.get("db_path", "trades.db"))
        self.bg_tasks = BackgroundTasks(self.config)
        self.sim_portfolio = None
        if self.config.get("simulation_mode", True):
            starting = self.config.get("starting_balance", 1000.0)
            state_file = self.config.get(
                "sim_state_file", "data/sim_state.json"
            )
            self.sim_portfolio = SimulatedPortfolio(
                starting_balance=starting, state_file=state_file
            )

    def start_all_bots(self):
        asyncio.create_task(self.bg_tasks.run_sentiment_loop())
        asyncio.create_task(heartbeat())

        if self.config.get("ENABLE_CRYPTO_TRADING", True):
            asyncio.create_task(self.start_crypto_bots())

        if self.config.get("ENABLE_STOCK_TRADING", False):
            asyncio.create_task(self.start_stock_bots())

        if self.config.get("FOREX_ENABLED", False):
            api_keys = self.config.get("api_keys", {})
            if api_keys.get("oanda") and api_keys.get("oanda_account_id"):
                asyncio.create_task(self.start_forex_bots())
            else:
                logging.warning("FOREX_ENABLED but OANDA credentials missing. Forex bots disabled.")

    async def start_crypto_bots(self):
        """Launch one or more crypto strategy instances."""
        logging.info(" Starting crypto bots...")

        api_keys = self.config["api_keys"]
        settings = self.config.get("crypto_settings", {})
        base_symbols_env = self.config.get("TRADE_SYMBOLS")
        base_symbols = (
            base_symbols_env
            if base_symbols_env
            else settings.get("trade_symbols", ["BTC-USD", "ETH-USD"])
        )

        extra_symbols: list[str] = []
        if self.config.get("ENABLE_AI_ASSET_DISCOVERY", False):
            from services.ai_strategist import ai_discover_assets

            try:
                extra_symbols = await ai_discover_assets(base_symbols)
            except Exception as e:
                logging.error(f"AI asset discovery failed: {e}")

        all_symbols = list(set(base_symbols + extra_symbols))

        crypto_api = CryptoAPI(
            api_key=api_keys.get("binance"),
            secret_key=api_keys.get("binance_secret", ""),
            simulation_mode=self.config.get("simulation_mode", True),
            portfolio=self.sim_portfolio,
            config=self.config,
        )

        await crypto_api.fetch_account_info()

        asyncio.create_task(start_crypto_market_feed(all_symbols))
        asyncio.create_task(start_coingecko_polling(all_symbols))

        strategy_cfgs = settings.get("strategies") or [settings]
        for cfg in strategy_cfgs:
            sym_list = cfg.get("trade_symbols", base_symbols)
            cfg_full = {**settings, **cfg}

            strat_type = cfg.get("type", "momentum").lower()
            if strat_type == "mean_reversion":
                from strategies.crypto.mean_reversion import MeanReversionStrategy as StratCls
            elif strat_type == "micro_scalping":
                from strategies.crypto.micro_scalping import MicroScalpingStrategy as StratCls
            elif strat_type == "pairs_trading":
                from strategies.crypto.pairs_trading import PairsTradingStrategy as StratCls
            else:
                StratCls = MomentumStrategy

            risk = RiskManager(crypto_api, cfg_full)
            await risk.update_equity()

            strategy = StratCls(
                api=crypto_api,
                risk=risk,
                config=cfg_full,
                db=self.db,
                symbol_list=sym_list,
                sentiment_source=self.bg_tasks,
                ai_symbols=extra_symbols,
            )

            asyncio.create_task(strategy.run())

    async def start_stock_bots(self):
        logging.info("Starting stock bots...")

        api_keys = self.config.get("api_keys", {})
        settings = self.config.get("stocks_settings", {})
        base_symbols = settings.get("trade_symbols", ["AAPL", "TSLA"])

        alpaca_key = api_keys.get("alpaca")
        alpaca_secret = api_keys.get("alpaca_secret")
        base_url = api_keys.get(
            "alpaca_base_url",
            "https://paper-api.alpaca.markets",
        )
        if not alpaca_key or not alpaca_secret:
            logging.error(
                "Alpaca API credentials missing. Stock bots disabled."
            )
            return

        from services.alpaca_manager import AlpacaManager

        stock_api = AlpacaManager(
            api_key=alpaca_key,
            api_secret=alpaca_secret,
            base_url=base_url,
            simulation_mode=self.config.get("simulation_mode", True),
            portfolio=self.sim_portfolio,
            config=self.config,
        )

        await stock_api.get_account()

        risk = RiskManager(stock_api, settings)
        await risk.update_equity()

        from data.market_data_stocks import start_stock_polling_loop

        asyncio.create_task(start_stock_polling_loop(base_symbols, stock_api))
        asyncio.create_task(
            start_stock_ws_feed(
                base_symbols,
                alpaca_key,
                alpaca_secret,
                base_url,
            )
        )

        strategy_cfgs = settings.get("strategies") or [settings]
        for cfg in strategy_cfgs:
            sym_list = cfg.get("trade_symbols", base_symbols)
            cfg_full = {**settings, **cfg}
            from strategies.stocks.stock_momentum import StockMomentumStrategy as StratCls
            risk = RiskManager(stock_api, cfg_full)
            await risk.update_equity()
            strategy = StratCls(
                api=stock_api,
                risk=risk,
                config=cfg_full,
                db=self.db,
                symbol_list=sym_list,
            )
            asyncio.create_task(strategy.run())

    async def start_forex_bots(self):
        logging.info("Starting forex bots...")

        api_keys = self.config.get("api_keys", {})
        settings = self.config.get("forex_settings", {})
        base_instruments = settings.get("trade_symbols", ["EUR_USD", "GBP_USD"])

        api_key = api_keys.get("oanda")
        account_id = api_keys.get("oanda_account_id")
        if not api_key or not account_id:
            logging.error(
                "OANDA API credentials missing or invalid. Bots disabled."
            )
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

        from data.market_data_forex import start_forex_polling_loop

        asyncio.create_task(
            start_forex_polling_loop(
                base_instruments,
                api_key,
                account_id,
            )
        )

        strategy_cfgs = settings.get("strategies") or [settings]
        for cfg in strategy_cfgs:
            inst_list = cfg.get("trade_symbols", base_instruments)
            cfg_full = {**settings, **cfg}
            from strategies.forex.rsi_trend import ForexRSITrendStrategy as StratCls
            risk = RiskManager(forex_api, cfg_full)
            await risk.update_equity()
            strategy = StratCls(
                api=forex_api,
                risk=risk,
                config=cfg_full,
                db=self.db,
                symbol_list=inst_list,
            )
            asyncio.create_task(strategy.run())
