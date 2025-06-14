import os
import unittest
from unittest import mock
from alpaca_client import _request

class AlpacaClientURLTest(unittest.TestCase):
    def test_request_url_join(self):
        os.environ['ALPACA_BASE_URL'] = 'https://paper-api.alpaca.markets/v2'

        captured = {}
        def fake_request(method, url, headers=None, timeout=10, **kwargs):
            captured['url'] = url
            class Resp:
                text = ''
                def raise_for_status(self):
                    pass
                def json(self):
                    return {}
            return Resp()

        with mock.patch('requests.request', side_effect=fake_request):
            _request('GET', '/v2/positions')

        self.assertEqual(captured['url'], 'https://paper-api.alpaca.markets/v2/positions')

if __name__ == '__main__':
    unittest.main()
