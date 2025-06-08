import json
import logging
from pathlib import Path
from datetime import datetime

class SimulatedPortfolio:
    """Simple portfolio tracker for simulation mode."""

    def __init__(self, starting_balance: float = 1000.0, state_file: str = "data/sim_state.json"):
        self.state_file = Path(state_file)
        self.starting_balance = starting_balance
        self.current_balance = starting_balance
        self.open_positions: dict[str, float] = {}
        self.trade_history: list[dict] = []
        self._load_state()

    def _load_state(self):
        if self.state_file.is_file():
            try:
                data = json.loads(self.state_file.read_text())
                self.starting_balance = data.get("starting_balance", self.starting_balance)
                self.current_balance = data.get("current_balance", self.starting_balance)
                self.open_positions = data.get("open_positions", {})
                self.trade_history = data.get("trade_history", [])
            except Exception as e:
                logging.error(f"Failed to load simulation state: {e}")
        else:
            logging.info("No existing simulation state found; starting fresh.")

    def _save_state(self):
        data = {
            "starting_balance": self.starting_balance,
            "current_balance": self.current_balance,
            "open_positions": self.open_positions,
            "trade_history": self.trade_history,
        }
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logging.error(f"Failed to save simulation state: {e}")

    def execute_trade(self, asset: str, action: str, size: float, price: float, confidence: float = 0.0):
        cost = size * price
        if action.lower() == "buy":
            self.current_balance -= cost
            self.open_positions[asset] = self.open_positions.get(asset, 0.0) + size
        else:
            self.current_balance += cost
            self.open_positions[asset] = self.open_positions.get(asset, 0.0) - size
            if abs(self.open_positions[asset]) < 1e-8:
                self.open_positions.pop(asset, None)

        trade = {
            "timestamp": datetime.utcnow().isoformat(),
            "asset": asset,
            "action": action,
            "size": size,
            "price": price,
            "confidence": confidence,
        }
        self.trade_history.append(trade)
        self._save_state()
        logging.info(
            f"[SIM] Executed {action.upper()} {size} {asset} @ ${price} | New balance: ${self.current_balance:.2f}"
        )
