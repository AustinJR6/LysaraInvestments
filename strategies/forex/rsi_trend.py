import asyncio
import logging
from indicators.technical_indicators import relative_strength_index
from risk.risk import DynamicRisk

class ForexRSITrendStrategy:
    """Simple RSI-based trend following strategy for Forex."""

    def __init__(self, api, risk, config, db, symbol_list):
        self.api = api
        self.risk = risk
        self.config = config
        self.db = db
        self.symbols = symbol_list
        self.price_history = {s: [] for s in symbol_list}
        self.interval = 10
        self.dynamic_risk = DynamicRisk(
            risk,
            config.get("atr_period", 14),
            config.get("volatility_multiplier", 3),
        )

    async def run(self):
        while True:
            for symbol in self.symbols:
                try:
                    data = await self.api.fetch_price(symbol)
                    price = float(data.get("bid") or 0)
                    self.price_history[symbol].append(price)

                    if len(self.price_history[symbol]) > 100:
                        self.price_history[symbol] = self.price_history[symbol][-100:]

                    rsi = relative_strength_index(self.price_history[symbol])
                    if rsi > 60:
                        await self.enter_trade(symbol, price, "buy", rsi)
                    elif rsi < 40:
                        await self.enter_trade(symbol, price, "sell", rsi)
                except Exception as e:
                    logging.error(f"[RSITrend] Error for {symbol}: {e}")
            await asyncio.sleep(self.interval)

    async def enter_trade(self, symbol, price, side, rsi):
        confidence = abs(rsi - 50) / 50
        qty = self.dynamic_risk.position_size(price, confidence, self.price_history[symbol])
        if qty <= 0:
            logging.warning(f"RSITrend: invalid position size for {symbol}")
            return

        await self.api.place_order(
            instrument=symbol,
            units=qty if side == "buy" else -qty,
            order_type="MARKET",
            price=price,
            confidence=confidence,
        )

        self.db.log_trade(
            symbol=symbol,
            side=side,
            quantity=qty,
            price=price,
            reason=f"rsi={rsi}",
            market="forex",
        )

        logging.info(f"{side.upper()} {symbol} @ {price} RSI={rsi} size={qty}")
