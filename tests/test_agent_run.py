import os
import unittest
from datetime import datetime

from lysara_investments.agent.market_snapshot import MarketSnapshot
from lysara_investments.agent.decision_engine import make_trade_decision
from lysara_investments.agent.memory import log_trade_decision
from lysara_investments.agent.personality import explain_decision


class AgentRunTest(unittest.TestCase):
    def test_snapshot_decision_logging(self):
        snapshot = MarketSnapshot(
            ticker="TEST",
            price=100.0,
            sentiment={"reddit": {"test": {"score": 0.5}}},
            technicals={},
            volatility=0.1,
            timestamp=datetime.utcnow(),
        )
        decision = make_trade_decision(snapshot, {"confidence_threshold": 0.1})
        explanation = explain_decision(
            snapshot.ticker,
            decision["action"],
            decision["rationale"],
            decision["confidence"],
        )
        self.assertEqual(decision["explanation"], explanation)
        self.assertIn("order", decision)
        self.assertEqual(decision["order"]["symbol"], "TEST")
        log_trade_decision(snapshot, decision)
        self.assertTrue(os.path.exists("logs/agent_history.json"))


if __name__ == "__main__":
    unittest.main()
