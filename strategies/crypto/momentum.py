# strategies/crypto/momentum.py

import asyncio
import logging
from datetime import datetime
import numpy as np

from risk.risk import DynamicRisk
from utils.helpers import parse_price
from services.ai_strategist import get_ai_trade_decision

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
                    context = self._build_context(symbol, price, sentiment)
                    decision = await get_ai_trade_decision(context)

                    if (
                        decision.get("action") in ["buy", "sell"]
                        and decision.get("confidence", 0) >= 0.7
                    ):
                        await self.enter_trade(
                            symbol,
                            price,
                            decision.get("action"),
                            decision.get("confidence", 0.0),
                            decision.get("reason", "ai"),
                        )
                    else:
                        logging.info(f"AI decision skipped: {decision}")

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

    def _build_context(self, symbol: str, price: float, sentiment: float) -> dict:
        prices = self.price_history[symbol]
        vol = float(np.std(np.diff(prices[-10:]))) if len(prices) > 2 else 0.0
        trend = "sideways"
        if len(prices) >= 5:
            x = np.arange(5)
            y = np.array(prices[-5:])
            slope = np.polyfit(x, y, 1)[0]
            if slope > 0:
                trend = "uptrend"
            elif slope < 0:
                trend = "downtrend"
        pos_qty = 0.0
        if getattr(self.api, "portfolio", None):
            pos_qty = self.api.portfolio.open_positions.get(symbol, 0.0)
        status = "flat"
        if pos_qty > 0:
            status = "long"
        elif pos_qty < 0:
            status = "short"
        support = min(prices[-20:]) if len(prices) >= 1 else price
        resistance = max(prices[-20:]) if len(prices) >= 1 else price
        return {
            "symbol": symbol,
            "price": price,
            "volatility": round(vol, 6),
            "sentiment": sentiment,
            "position_status": status,
            "recent_trend": trend,
            "support": support,
            "resistance": resistance,
            "drawdown": self.risk.daily_loss,
            "loss_streak": self.risk.consec_losses,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def enter_trade(
        self, symbol: str, price: float, action: str, confidence: float, reason: str
    ):
        if not await self.risk.check_daily_loss():
            logging.warning("Daily loss limit reached. Trade blocked.")
            return
        qty = self.dynamic_risk.position_size(price, confidence, self.price_history[symbol])
        if qty <= 0:
            logging.warning("Momentum: invalid position size.")
            return

        stops = self.dynamic_risk.stop_levels(price, action, self.price_history[symbol])
        if stops.rr < 1.0:
            logging.info(f"Trade skipped on {symbol} due to RR {stops.rr:.2f}")
            return

        if not self.config.get("simulation_mode", True) and not self.config.get("LIVE_TRADING_ENABLED", True):
            logging.info("Live trading disabled. Trade skipped.")
            return

        await self.api.place_order(
            product_id=symbol,
            side=action,
            size=qty,
            order_type="market",
            price=price,
            confidence=confidence,
        )

        self.db.log_trade(
            symbol=symbol,
            side=action,
            quantity=qty,
            price=price,
            profit_loss=None,
            reason=reason,
            market="crypto",
        )

        logging.info(
            f"{action.upper()} {symbol} @ {price} conf={confidence} RR={stops.rr:.2f} details={reason}"
        )
