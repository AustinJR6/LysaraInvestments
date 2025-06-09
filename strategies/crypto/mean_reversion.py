# strategies/crypto/mean_reversion.py

import asyncio
import logging
from indicators.technical_indicators import moving_average

class MeanReversionStrategy:
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

                    ma = moving_average(self.price_history[symbol], 20)

                    if price < 0.98 * ma:
                        await self.enter_trade(symbol, price, "buy")
                    elif price > 1.02 * ma:
                        await self.enter_trade(symbol, price, "sell")

                except Exception as e:
                    logging.error(f"[MeanReversion] Error on {symbol}: {e}")

            await asyncio.sleep(self.interval)

    async def enter_trade(self, symbol, price, side):
        if not await self.risk.check_daily_loss():
            logging.warning("Daily loss limit reached. Trade blocked.")
            return
        qty = self.risk.get_position_size(price)
        if qty <= 0:
            logging.warning("Position size is zero or invalid.")
            return

        order = await self.api.place_order(
            product_id=symbol,
            side=side,
            size=qty,
            price=price,
            order_type="market",
            confidence=0.0,
        )

        self.db.log_trade(
            symbol=symbol,
            side=side,
            quantity=qty,
            price=price,
            profit_loss=None,
            reason="mean_reversion",
            market="crypto"
        )

        logging.info(f"Executed {side.upper()} {symbol} @ {price} [Mean Reversion]")
