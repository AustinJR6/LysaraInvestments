# strategies/crypto/momentum.py

import asyncio
import logging
from indicators.technical_indicators import relative_strength_index

class MomentumStrategy:
    def __init__(self, api, risk, config, db, symbol_list):
        self.api = api
        self.risk = risk
        self.config = config
        self.db = db
        self.symbols = symbol_list
        self.price_history = {symbol: [] for symbol in symbol_list}
        self.interval = 10  # seconds

    async def run(self):
        while True:
            for symbol in self.symbols:
                try:
                    data = await self.api.fetch_market_price(symbol)
                    price = float(data.get("price", 0))
                    self.price_history[symbol].append(price)

                    if len(self.price_history[symbol]) > 100:
                        self.price_history[symbol] = self.price_history[symbol][-100:]

                    rsi = relative_strength_index(self.price_history[symbol])

                    if rsi > 70:
                        await self.enter_trade(symbol, price, "sell", rsi)
                    elif rsi < 30:
                        await self.enter_trade(symbol, price, "buy", rsi)

                except Exception as e:
                    logging.error(f"[Momentum] Error on {symbol}: {e}")

            await asyncio.sleep(self.interval)

    async def enter_trade(self, symbol, price, side, rsi):
        qty = self.risk.get_position_size(price)
        if qty <= 0:
            logging.warning("Momentum: invalid position size.")
            return

        order = await self.api.place_order(
            product_id=symbol,
            side=side,
            size=qty,
            order_type="market"
        )

        self.db.log_trade(
            symbol=symbol,
            side=side,
            quantity=qty,
            price=price,
            profit_loss=None,
            reason=f"momentum_rsi_{rsi}",
            market="crypto"
        )

        logging.info(f"{side.upper()} {symbol} @ {price} triggered by RSI={rsi}")
