# strategies/crypto/momentum.py

import asyncio
import logging
from signals import SignalGenerator, Signal
from risk.risk import DynamicRisk
from utils.helpers import parse_price

class MomentumStrategy:
    def __init__(self, api, risk, config, db, symbol_list, sentiment_source=None):
        self.api = api
        self.risk = risk
        self.config = config
        self.db = db
        self.symbols = symbol_list
        self.sentiment_source = sentiment_source
        self.price_history = {symbol: [] for symbol in symbol_list}
        self.interval = 10  # seconds
        self.signal_gen = SignalGenerator()
        self.dynamic_risk = DynamicRisk(risk,
                                       config.get("atr_period", 14),
                                       config.get("volatility_multiplier", 3))

    async def run(self):
        while True:
            for symbol in self.symbols:
                try:
                    data = await self.api.fetch_market_price(symbol)
                    price = parse_price(data)
                    self.price_history[symbol].append(price)

                    if len(self.price_history[symbol]) > 100:
                        self.price_history[symbol] = self.price_history[symbol][-100:]

                    sentiment = await self.get_sentiment(symbol)
                    signal = self.signal_gen.generate(self.price_history[symbol], sentiment)

                    if signal.action != "hold" and signal.confidence > 0:
                        await self.enter_trade(symbol, price, signal)

                except Exception as e:
                    logging.error(f"[Momentum] Error on {symbol}: {e}")

            await asyncio.sleep(self.interval)

    async def get_sentiment(self, symbol: str) -> float:
        if not self.sentiment_source:
            return 0.0
        scores = self.sentiment_source.sentiment_scores
        cp = scores.get("cryptopanic", {}).get(symbol, {}).get("score", 0.0)
        reddit_data = scores.get("reddit", {})
        reddit_avg = 0.0
        if reddit_data:
            for sub in reddit_data.values():
                reddit_avg += sub.get("score", 0.0)
            reddit_avg /= max(len(reddit_data), 1)
        news = scores.get("newsapi", {}).get("score", 0.0)
        return (cp + reddit_avg + news) / 3

    async def enter_trade(self, symbol: str, price: float, signal: Signal):
        qty = self.dynamic_risk.position_size(price, signal.confidence, self.price_history[symbol])
        if qty <= 0:
            logging.warning("Momentum: invalid position size.")
            return

        stops = self.dynamic_risk.stop_levels(price, signal.action, self.price_history[symbol])
        if stops.rr < 1.0:
            logging.info(f"Trade skipped on {symbol} due to RR {stops.rr:.2f}")
            return

        await self.api.place_order(
            product_id=symbol,
            side=signal.action,
            size=qty,
            order_type="market",
            price=price,
            confidence=signal.confidence,
        )

        self.db.log_trade(
            symbol=symbol,
            side=signal.action,
            quantity=qty,
            price=price,
            profit_loss=None,
            reason=signal.details,
            market="crypto",
        )

        logging.info(
            f"{signal.action.upper()} {symbol} @ {price} conf={signal.confidence} RR={stops.rr:.2f} details={signal.details}"
        )
