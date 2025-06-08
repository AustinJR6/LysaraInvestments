# strategies/stocks/earnings_play.py

import asyncio
import logging

class EarningsPlayStrategy:
    def __init__(self, api, risk, config, db, symbol_list):
        self.api = api
        self.risk = risk
        self.config = config
        self.db = db
        self.symbols = symbol_list
        self.interval = 60  # Check every 60 seconds

    async def run(self):
        while True:
            for symbol in self.symbols:
                try:
                    price_data = await self.api.fetch_market_price(symbol)
                    price = float(price_data.get("price") or price_data.get("last_trade_price", 0))
                    # Placeholder logic for earnings flag
                    earnings_soon = self.mock_earnings_event(symbol)

                    if earnings_soon:
                        await self.enter_trade(symbol, price, "buy")

                except Exception as e:
                    logging.error(f"[EarningsPlay] Error for {symbol}: {e}")

            await asyncio.sleep(self.interval)

    def mock_earnings_event(self, symbol):
        """Stub for earnings calendar integration."""
        # Replace this with actual API-based detection in future
        return symbol.endswith("L")  # dumb logic to simulate

    async def enter_trade(self, symbol, price, side):
        qty = self.risk.get_position_size(price)
        if qty <= 0:
            logging.warning(f"EarningsPlay: invalid position size for {symbol}")
            return

        await self.api.place_order(
            symbol=symbol,
            side=side,
            quantity=qty,
            order_type="market"
        )

        self.db.log_trade(
            symbol=symbol,
            side=side,
            quantity=qty,
            price=price,
            reason="earnings_play",
            market="stocks"
        )

        logging.info(f"{side.upper()} {symbol} earnings play triggered at {price}")
