import asyncio
import logging
from typing import List, Dict

from api.crypto_api import CryptoAPI
from services.alpaca_manager import AlpacaManager
from api.forex_api import ForexAPI
from services.sim_portfolio import SimulatedPortfolio


class PortfolioManager:
    """Helper to load live and simulated portfolio information."""

    def __init__(self, config: Dict):
        self.config = config or {}
        starting = self.config.get("starting_balance", 1000.0)
        state_file = self.config.get("sim_state_file", "data/sim_state.json")
        self.sim_portfolio = SimulatedPortfolio(
            starting_balance=starting, state_file=state_file
        )

    async def _fetch_live_holdings(self) -> List[Dict]:
        """Fetch holdings from available API integrations."""
        holdings: List[Dict] = []
        api_keys = self.config.get("api_keys", {})

        # Crypto holdings via Coinbase
        if api_keys.get("coinbase"):
            try:
                api = CryptoAPI(
                    api_key=api_keys.get("coinbase"),
                    secret_key=api_keys.get("coinbase_secret", ""),
                    simulation_mode=False,
                )
                data = await api.fetch_holdings()
                for asset, qty in data.items():
                    price = await api.fetch_market_price(f"{asset}-USD")
                    curr = float(price.get("price", 0))
                    holdings.append(
                        {
                            "asset": asset,
                            "quantity": qty,
                            "entry_price": None,
                            "current_price": curr,
                            "pnl": None,
                        }
                    )
                await api.close()
            except Exception as e:
                logging.error(f"Failed to fetch crypto holdings: {e}")

        # Stock holdings via Alpaca
        if api_keys.get("alpaca") and api_keys.get("alpaca_secret"):
            try:
                api = AlpacaManager(
                    api_key=api_keys.get("alpaca"),
                    api_secret=api_keys.get("alpaca_secret"),
                    base_url=api_keys.get("alpaca_base_url", "https://paper-api.alpaca.markets"),
                    simulation_mode=False,
                )
                positions = await api.get_positions()
                for p in positions:
                    holdings.append(
                        {
                            "asset": p.symbol,
                            "quantity": float(p.qty),
                            "entry_price": float(p.avg_entry_price),
                            "current_price": float(p.current_price),
                            "pnl": float(p.unrealized_pl),
                        }
                    )
            except Exception as e:
                logging.error(f"Failed to fetch stock holdings: {e}")

        # Placeholder for forex holdings
        if api_keys.get("oanda") and api_keys.get("oanda_account"):
            try:
                api = ForexAPI(
                    api_key=api_keys.get("oanda"),
                    account_id=api_keys.get("oanda_account"),
                    simulation_mode=False,
                )
                info = await api.get_account_info()
                balance = float(info.get("balance", 0))
                holdings.append(
                    {
                        "asset": "Forex Account",
                        "quantity": balance,
                        "entry_price": None,
                        "current_price": balance,
                        "pnl": None,
                    }
                )
                await api.close()
            except Exception as e:
                logging.error(f"Failed to fetch forex holdings: {e}")

        return holdings

    async def _fetch_crypto_holdings(self) -> List[Dict]:
        """Fetch crypto holdings via Coinbase."""
        holdings: List[Dict] = []
        api_keys = self.config.get("api_keys", {})
        if not api_keys.get("coinbase"):
            return holdings
        try:
            api = CryptoAPI(
                api_key=api_keys.get("coinbase"),
                secret_key=api_keys.get("coinbase_secret", ""),
                simulation_mode=False,
            )
            data = await api.fetch_holdings()
            for asset, qty in data.items():
                price = await api.fetch_market_price(f"{asset}-USD")
                curr = float(price.get("price", 0))
                holdings.append(
                    {
                        "asset": asset,
                        "quantity": qty,
                        "entry_price": None,
                        "current_price": curr,
                        "pnl": None,
                    }
                )
            await api.close()
        except Exception as e:
            logging.error(f"Failed to fetch crypto holdings: {e}")
        return holdings

    async def _fetch_stock_holdings(self) -> List[Dict]:
        """Fetch stock holdings via Alpaca."""
        holdings: List[Dict] = []
        api_keys = self.config.get("api_keys", {})
        if not (api_keys.get("alpaca") and api_keys.get("alpaca_secret")):
            return holdings
        try:
            api = AlpacaManager(
                api_key=api_keys.get("alpaca"),
                api_secret=api_keys.get("alpaca_secret"),
                base_url=api_keys.get("alpaca_base_url", "https://paper-api.alpaca.markets"),
                simulation_mode=False,
            )
            positions = await api.get_positions()
            for p in positions:
                holdings.append(
                    {
                        "asset": p.symbol,
                        "quantity": float(p.qty),
                        "entry_price": float(p.avg_entry_price),
                        "current_price": float(p.current_price),
                        "pnl": float(p.unrealized_pl),
                    }
                )
        except Exception as e:
            logging.error(f"Failed to fetch stock holdings: {e}")
        return holdings

    async def _fetch_forex_holdings(self) -> List[Dict]:
        """Fetch forex account balance via OANDA."""
        holdings: List[Dict] = []
        api_keys = self.config.get("api_keys", {})
        if not (api_keys.get("oanda") and api_keys.get("oanda_account")):
            return holdings
        try:
            api = ForexAPI(
                api_key=api_keys.get("oanda"),
                account_id=api_keys.get("oanda_account"),
                simulation_mode=False,
            )
            info = await api.get_account_info()
            balance = float(info.get("balance", 0))
            holdings.append(
                {
                    "asset": "Forex Account",
                    "quantity": balance,
                    "entry_price": None,
                    "current_price": balance,
                    "pnl": None,
                }
            )
            await api.close()
        except Exception as e:
            logging.error(f"Failed to fetch forex holdings: {e}")
        return holdings

    async def _fetch_all_holdings(self) -> Dict[str, List[Dict]]:
        """Fetch holdings for all asset classes separately."""
        crypto = await self._fetch_crypto_holdings()
        stocks = await self._fetch_stock_holdings()
        forex = await self._fetch_forex_holdings()
        return {"crypto": crypto, "stocks": stocks, "forex": forex}

    def get_live_holdings(self) -> List[Dict]:
        try:
            return asyncio.run(self._fetch_live_holdings())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._fetch_live_holdings())
            loop.close()
            return result

    def get_account_holdings(self) -> Dict[str, List[Dict]]:
        """Return real holdings for crypto, stocks and forex separately."""
        try:
            return asyncio.run(self._fetch_all_holdings())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._fetch_all_holdings())
            loop.close()
            return result

    def get_simulated_portfolio(self) -> Dict:
        """Load simulated portfolio state from file."""
        self.sim_portfolio._load_state()
        positions = []
        for asset, qty in self.sim_portfolio.open_positions.items():
            positions.append(
                {
                    "asset": asset,
                    "quantity": qty,
                    "entry_price": None,
                    "current_price": 0.0,
                    "pnl": None,
                }
            )

        trades = self.sim_portfolio.trade_history
        closed = [t for t in trades if t.get("pnl") is not None]
        wins = [t for t in closed if t.get("pnl", 0) > 0]
        win_rate = round(len(wins) / len(closed) * 100, 2) if closed else 0.0
        avg_return = (
            round(sum(t.get("pnl", 0) for t in closed) / len(closed), 4)
            if closed
            else 0.0
        )

        summary = {
            "win_rate": win_rate,
            "avg_return": avg_return,
            "trade_count": len(trades),
        }

        return {
            "balance": self.sim_portfolio.current_balance,
            "positions": positions,
            "trades": trades,
            "summary": summary,
        }
