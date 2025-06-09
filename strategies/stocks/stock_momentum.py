# strategies/stocks/stock_momentum.py

import asyncio
import logging
from datetime import datetime
import numpy as np

from indicators.technical_indicators import moving_average
from services.ai_strategist import get_ai_trade_decision

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

                    if len(self.price_history[symbol]) > 100:
                        self.price_history[symbol] = self.price_history[symbol][-100:]

                    context = self._build_context(symbol, price)
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
                    logging.error(f"[StockMomentum] Error for {symbol}: {e}")

            await asyncio.sleep(self.interval)

    def _build_context(self, symbol: str, price: float) -> dict:
        prices = self.price_history[symbol]
        vol = float(np.std(np.diff(prices[-10:]))) if len(prices) > 2 else 0.0
        trend = "sideways"
        if len(prices) >= 5:
            x = np.arange(5)
            y = np.array(prices[-5:])
            slope = np.polyfit(x, y, 1)[0]
            trend = "uptrend" if slope > 0 else "downtrend" if slope < 0 else "sideways"
        status = "flat"
        if getattr(self.api, "portfolio", None):
            qty = self.api.portfolio.open_positions.get(symbol, 0.0)
            if qty > 0:
                status = "long"
            elif qty < 0:
                status = "short"
        support = min(prices[-20:]) if prices else price
        resistance = max(prices[-20:]) if prices else price
        return {
            "symbol": symbol,
            "price": price,
            "volatility": round(vol, 6),
            "sentiment": 0.0,
            "position_status": status,
            "recent_trend": trend,
            "support": support,
            "resistance": resistance,
            "drawdown": self.risk.daily_loss,
            "loss_streak": self.risk.consec_losses,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def enter_trade(self, symbol, price, side, confidence):
        if not await self.risk.check_daily_loss():
            logging.warning("Daily loss limit reached. Trade blocked.")
            return
        qty = self.risk.get_position_size(price)
        if qty <= 0:
            logging.warning(f"StockMomentum: invalid position size for {symbol}")
            return

        if not self.config.get("simulation_mode", True) and not self.config.get("LIVE_TRADING_ENABLED", True):
            logging.info("Live trading disabled. Trade skipped.")
            return

        await self.api.place_order(
            symbol=symbol,
            side=side,
            quantity=qty,
            order_type="market",
            price=price,
            confidence=confidence,
        )

        self.db.log_trade(
            symbol=symbol,
            side=side,
            quantity=qty,
            price=price,
            reason="ai",
            market="stocks"
        )

        logging.info(
            f"{side.upper()} {symbol} @ {price} conf={confidence} via ai strategist"
        )
