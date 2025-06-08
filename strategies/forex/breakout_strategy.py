# strategies/forex/breakout_strategy.py

import asyncio
import logging

class BreakoutStrategy:
    def __init__(self, api, risk, config, db, symbol_list):
        self.api = api
        self.risk = risk
        self.config = config
        self.db = db
        self.symbols = symbol_list
        self.price_history = {symbol: [] for symbol in symbol_list}
        self.lookback = 20  # candles
        self.interval = 15  # seconds

    async def run(self):
        while True:
            for symbol in self.symbols:
                try:
                    data = await self.api.fetch_price(symbol)
                    price = float(data.get("bid") or 0)
                    self.price_history[symbol].append(price)

                    if len(self.price_history[symbol]) > self.lookback:
                        self.price_history[symbol] = self.price_history[symbol][-self.lookback:]

                        recent = self.price_history[symbol]
                        high = max(recent)
                        low = min(recent)

                        if price > high:
                            await self.enter_trade(symbol, price, "buy")
                        elif price < low:
                            await self.enter_trade(symbol, price, "sell")

                except Exception as e:
                    logging.error(f"[Breakout] Error for {symbol}: {e}")

            await asyncio.sleep(self.interval)

    async def enter_trade(self, symbol, price, side):
        qty = self.risk.get_position_size(price)
        if qty <= 0:
            logging.warning(f"BreakoutStrategy: invalid position size for {symbol}")
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
            reason="breakout_strategy",
            market="forex"
        )

        logging.info(f"{side.upper()} {symbol} breakout @ {price}")
