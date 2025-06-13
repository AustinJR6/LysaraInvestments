# strategies/crypto/pairs_trading.py

import asyncio
import logging
from indicators.technical_indicators import moving_average
from strategies.base_strategy import BaseStrategy

class PairsTradingStrategy(BaseStrategy):
    def __init__(self, api, risk, config, db, pair=("ETH-USD", "BTC-USD")):
        super().__init__(api, risk, config, db, pair)
        self.pair = pair
        self.interval = 15  # seconds

    async def run(self):
        while True:
            try:
                price_1 = await self.get_price(self.pair[0])
                price_2 = await self.get_price(self.pair[1])

                self.price_history[self.pair[0]].append(price_1)
                self.price_history[self.pair[1]].append(price_2)

                for sym in self.pair:
                    if len(self.price_history[sym]) > 100:
                        self.price_history[sym] = self.price_history[sym][-100:]

                spread = price_1 - price_2
                spread_hist = [
                    p1 - p2 for p1, p2 in zip(self.price_history[self.pair[0]], self.price_history[self.pair[1]])
                ]

                spread_ma = moving_average(spread_hist, 20)

                if spread > spread_ma * 1.05:
                    await self.trade_pair("short", price_1, price_2, spread)
                elif spread < spread_ma * 0.95:
                    await self.trade_pair("long", price_1, price_2, spread)

            except Exception as e:
                logging.error(f"[PairsTrading] Error: {e}")

            await asyncio.sleep(self.interval)

    async def get_price(self, symbol):
        data = await self.api.fetch_market_price(symbol)
        return float(data.get("price", 0))

    async def trade_pair(self, direction: str, price_1: float, price_2: float, spread: float):
        if not await self.risk.check_daily_loss():
            logging.warning("Daily loss limit reached. Trade blocked.")
            return
        qty_1 = self.risk.get_position_size(price_1)
        qty_2 = self.risk.get_position_size(price_2)

        if direction == "long":
            # Buy 1, Sell 2
            await self.api.place_order(product_id=self.pair[0], side="buy", size=qty_1, price=price_1, confidence=0.0)
            await self.api.place_order(product_id=self.pair[1], side="sell", size=qty_2, price=price_2, confidence=0.0)
        else:
            # Sell 1, Buy 2
            await self.api.place_order(product_id=self.pair[0], side="sell", size=qty_1, price=price_1, confidence=0.0)
            await self.api.place_order(product_id=self.pair[1], side="buy", size=qty_2, price=price_2, confidence=0.0)

        self.db.log_trade(
            symbol=f"{self.pair[0]}+{self.pair[1]}",
            side=direction,
            quantity=1.0,
            price=spread,
            profit_loss=None,
            reason="pairs_trading",
            market="crypto"
        )

        logging.info(f"[PAIRS] {direction.upper()} pair {self.pair} on spread {spread}")
