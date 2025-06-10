import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict

import aiohttp
from config.config_manager import ConfigManager
from signals.signal_fusion_engine import SignalFusionEngine

COINGECKO_URL = "https://api.coingecko.com/api/v3/search/trending"

class OpportunityScanner:
    """Background service to find trending crypto opportunities."""

    def __init__(self, config: Dict):
        self.config = config
        self.trade_symbols = set(config.get("TRADE_SYMBOLS", []))
        self.temp_symbols: Dict[str, datetime] = {}
        self.fusion = SignalFusionEngine(config)

    async def fetch_trending(self) -> List[str]:
        async with aiohttp.ClientSession() as session:
            async with session.get(COINGECKO_URL) as resp:
                data = await resp.json()
                coins = data.get("coins", [])
                return [c["item"]["symbol"].upper() + "-USD" for c in coins[:7]]

    def cleanup_temp(self):
        now = datetime.utcnow()
        for sym, ts in list(self.temp_symbols.items()):
            if now - ts > timedelta(hours=1):
                self.temp_symbols.pop(sym, None)

    async def scan(self) -> List[Dict]:
        results = []
        trending = await self.fetch_trending()
        for symbol in trending:
            if symbol in self.trade_symbols:
                continue
            prices = []  # placeholder for price history
            score_data = await self.fusion.score_symbol(symbol, prices)
            results.append(
                {
                    "symbol": symbol,
                    "score": score_data.conviction,
                    "details": score_data.details,
                }
            )
            self.temp_symbols[symbol] = datetime.utcnow()
        self.cleanup_temp()
        top = sorted(results, key=lambda x: x["score"], reverse=True)[:3]
        logging.info(f"OpportunityScanner found: {top}")
        return top

    def get_active_symbols(self) -> List[str]:
        self.cleanup_temp()
        return list(self.trade_symbols | set(self.temp_symbols.keys()))

async def main():
    config = ConfigManager().load_config()
    scanner = OpportunityScanner(config)
    await scanner.scan()

if __name__ == "__main__":
    asyncio.run(main())
