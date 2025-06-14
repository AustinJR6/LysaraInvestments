import json
import tempfile
import unittest
from pathlib import Path

from signals import sentiment_manager

class SentimentManagerTest(unittest.TestCase):
    def test_aggregated_score(self):
        data = {
            "cryptopanic": {"BTC-USD": {"score": 0.2}},
            "reddit": {"crypto": {"score": 0.4}},
            "newsapi": {"score": -0.1},
        }
        with tempfile.NamedTemporaryFile('w+', delete=False) as tmp:
            json.dump(data, tmp)
            tmp.flush()
            sentiment_manager.SENTIMENT_PATH = Path(tmp.name)
            score = sentiment_manager.get_sentiment_score("BTC-USD")
        expected = (0.2 + 0.4 - 0.1) / 3
        self.assertAlmostEqual(score, expected, places=6)

if __name__ == '__main__':
    unittest.main()
