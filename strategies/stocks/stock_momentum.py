# strategies/stocks/stock_momentum.py

import asyncio
import logging
from indicators.technical_indicators import moving_average

class StockMomentumStrategy:
    def __init__(self, api, risk, config, db, symbol_list):
        self.api = api
        self.risk = risk
        self.config = config
        self.db = db
        self.symbols = symbol_list
        self.price_history = {symbol: [] for symbol in symbol_list}
        self.ma_period = config.get("moving_average_period", 20)
        self.interval = 30  # seconds

    async def run(self):
        while True:
            for symbol in self.symbols:
                try:
                    price_data = await self.api.fetch_market_price(symbol)
                    price = float(price_data.get("price") or price_data.get("last_trade_price", 0))
                    self.price_history[symbol].append(price)

                    if len(self.price_history[symbol]) > self.ma_period:
                        self.price_history[symbol] = self.price_history[symbol][-self.ma_period:]
                        ma = moving_average(self.price_history[symbol], self.ma_period)

                        if price > ma * 1.02:
                            await self.enter_trade(symbol, price, "buy")

                except Exception as e:
                    logging.error(f"[StockMomentum] Error for {symbol}: {e}")

            await asyncio.sleep(self.interval)

    async def enter_trade(self, symbol, price, side):
        if not await self.risk.check_daily_loss():
            logging.warning("Daily loss limit reached. Trade blocked.")
            return
        qty = self.risk.get_position_size(price)
        if qty <= 0:
            logging.warning(f"StockMomentum: invalid position size for {symbol}")
            return

        await self.api.place_order(
            symbol=symbol,
            side=side,
            quantity=qty,
            order_type="market",
            price=price,
            confidence=0.0,
        )

        self.db.log_trade(
            symbol=symbol,
            side=side,
            quantity=qty,
            price=price,
            reason="momentum",
            market="stocks"
        )

        logging.info(f"{side.upper()} {symbol} @ {price} via momentum strategy")
