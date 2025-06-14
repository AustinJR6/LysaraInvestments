import unittest
import asyncio
from api.crypto_api import CryptoAPI

class CryptoAPITest(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_holdings_alias(self):
        api = CryptoAPI(api_key="dummy", simulation_mode=True)
        api._mock_holdings = {"BTC": 1.0}
        holdings = await api.fetch_holdings()
        self.assertEqual(holdings, {"BTC": 1.0})

if __name__ == "__main__":
    unittest.main()
