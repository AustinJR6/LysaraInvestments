from __future__ import annotations

import asyncio
import logging
from indicators.technical_indicators import relative_strength_index
from strategies.base_strategy import BaseStrategy

class MicroScalpingStrategy(BaseStrategy):
    """High-frequency momentum scalper using 5-min RSI."""

    def __init__(self, api, risk, config, db, symbol_list):
        super().__init__(api, risk, config, db, symbol_list)
        self.interval = 5  # seconds
        self.rsi_period = 6
        self.hold_bars = 1

    async def run(self):
        while True:
            for symbol in self.symbols:
                try:
                    data = await self.api.fetch_market_price(symbol)
                    price = float(data.get("price") or data.get("bid") or 0)
                    self.price_history[symbol].append(price)
                    if len(self.price_history[symbol]) > self.rsi_period + 2:
                        self.price_history[symbol] = self.price_history[symbol][- (self.rsi_period + 2):]
                        rsi = relative_strength_index(self.price_history[symbol], self.rsi_period)
                        if rsi > 55:
                            await self.enter_trade(symbol, price, "buy")
                        elif rsi < 45:
                            await self.enter_trade(symbol, price, "sell")
                except Exception as e:
                    logging.error(f"[MicroScalp] Error for {symbol}: {e}")
            await asyncio.sleep(self.interval)

    async def enter_trade(self, symbol: str, price: float, side: str):
        if not await self.risk.check_daily_loss():
            logging.warning("Daily loss limit reached. Trade blocked.")
            return
        qty = self.risk.get_position_size(price)
        if qty <= 0:
            logging.warning("MicroScalping: invalid position size")
            return
        await self.api.place_order(
            product_id=symbol,
            side=side,
            size=qty,
            order_type="market",
            price=price,
            confidence=0.0,
        )
        self.db.log_trade(
            symbol=symbol,
            side=side,
            quantity=qty,
            price=price,
            profit_loss=None,
            reason="micro_scalp",
            market="crypto",
        )
        logging.info(f"{side.upper()} {symbol} micro scalp @ {price}")
