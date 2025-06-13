import asyncio
import unittest
from risk.risk_manager import RiskManager

class DummyAPI:
    def __init__(self, balance=1000):
        self.balance = balance
    async def fetch_account_info(self):
        return {"balance": self.balance}

class RiskManagerTest(unittest.IsolatedAsyncioTestCase):
    async def test_position_size(self):
        api = DummyAPI()
        cfg = {"risk_per_trade": 0.02, "api_keys": {}}
        rm = RiskManager(api, cfg)
        await rm.update_equity()
        size = rm.get_position_size(100)
        self.assertAlmostEqual(size, 0.2, places=6)

    async def test_drawdown_trigger(self):
        api = DummyAPI(1000)
        cfg = {"risk_per_trade": 0.02, "max_daily_loss": -10, "api_keys": {}}
        rm = RiskManager(api, cfg)
        await rm.update_equity()
        rm.record_loss(-20)
        self.assertTrue(rm.drawdown_triggered)

if __name__ == '__main__':
    unittest.main()
