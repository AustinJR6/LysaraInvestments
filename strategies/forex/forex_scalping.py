# strategies/forex/forex_scalping.py

import asyncio
import logging
from indicators.technical_indicators import exponential_moving_average

class ForexScalpingStrategy:
    def __init__(self, api, risk, config, db, symbol_list):
        self.api = api
        self.risk = risk
        self.config = config
        self.db = db
        self.symbols = symbol_list
        self.price_history = {symbol: [] for symbol in symbol_list}
        self.interval = 5  # seconds
        self.ema_period = 9

    async def run(self):
        while True:
            for symbol in self.symbols:
                try:
                    data = await self.api.fetch_price(symbol)
                    price = float(data.get("bid") or 0)
                    self.price_history[symbol].append(price)

                    if len(self.price_history[symbol]) > self.ema_period:
                        self.price_history[symbol] = self.price_history[symbol][-self.ema_period:]
                        ema = exponential_moving_average(self.price_history[symbol], self.ema_period)

                        if price > ema:
                            await self.enter_trade(symbol, price, "buy")
                        elif price < ema:
                            await self.enter_trade(symbol, price, "sell")

                except Exception as e:
                    logging.error(f"[Scalping] Error for {symbol}: {e}")

            await asyncio.sleep(self.interval)

    async def enter_trade(self, symbol, price, side):
        qty = self.risk.get_position_size(price)
        if qty <= 0:
            logging.warning(f"ScalpingStrategy: invalid position size for {symbol}")
            return

        await self.api.place_order(
            instrument=symbol,
            units=qty if side == "buy" else -qty,
            order_type="MARKET"
        )

        self.db.log_trade(
            symbol=symbol,
            side=side,
            quantity=qty,
            price=price,
            reason="scalping",
            market="forex"
        )

        logging.info(f"{side.upper()} {symbol} SCALP @ {price}")
