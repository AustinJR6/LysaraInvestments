# strategies/base_strategy.py

import abc

class BaseStrategy(abc.ABC):
    """
    Abstract base class for trading strategies.
    """

    def __init__(self, api, risk, config, db, symbol_list):
        self.api = api
        self.risk = risk
        self.config = config
        self.db = db
        self.symbols = symbol_list
        self.price_history = {symbol: [] for symbol in symbol_list}

    @abc.abstractmethod
    async def run(self):
        """
        Run the main strategy loop.
        """
        pass

    @abc.abstractmethod
    async def enter_trade(self, symbol: str, price: float, side: str):
        """
        Submit a new trade with direction and log it.
        """
        pass
