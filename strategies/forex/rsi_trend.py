import asyncio
import logging
from datetime import datetime
import numpy as np
from indicators.technical_indicators import relative_strength_index
from risk.risk import DynamicRisk
from services.ai_strategist import get_ai_trade_decision
from strategies.base_strategy import BaseStrategy

class ForexRSITrendStrategy(BaseStrategy):
    """Simple RSI-based trend following strategy for Forex."""

    def __init__(self, api, risk, config, db, symbol_list):
        super().__init__(api, risk, config, db, symbol_list)
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
                    logging.error(f"[RSITrend] Error for {symbol}: {e}")
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

    async def enter_trade(self, symbol, price, side, confidence, reason):
        qty = self.dynamic_risk.position_size(price, confidence, self.price_history[symbol])
        if qty <= 0:
            logging.warning(f"RSITrend: invalid position size for {symbol}")
            return

        if not self.config.get("simulation_mode", True) and not self.config.get("LIVE_TRADING_ENABLED", True):
            logging.info("Live trading disabled. Trade skipped.")
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
            reason=reason,
            market="forex",
        )

        logging.info(
            f"{side.upper()} {symbol} @ {price} conf={confidence} reason={reason} size={qty}"
        )
