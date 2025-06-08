# risk/risk_manager.py

import logging

class RiskManager:
    def __init__(self, api_client, config: dict):
        self.api = api_client
        self.config = config
        self.max_drawdown = config.get("max_drawdown", 0.2)
        self.max_daily_loss = config.get("max_daily_loss", -200)
        self.risk_per_trade = config.get("risk_per_trade", 0.02)
        self.max_consec_losses = config.get("max_consec_losses", 5)
        self.drawdown_triggered = False
        self.daily_loss = 0.0
        self.consec_losses = 0
        self.last_equity = None

    async def update_equity(self):
        info = await self.api.fetch_account_info()
        if isinstance(info, dict) and "balance" in info:
            self.last_equity = float(info["balance"])
        elif "portfolio_value" in info:
            self.last_equity = float(info["portfolio_value"])
        else:
            logging.warning("RiskManager: Could not retrieve equity from API.")
        return self.last_equity

    def get_position_size(self, price: float) -> float:
        if not self.last_equity or self.risk_per_trade <= 0:
            return 0
        dollar_risk = self.last_equity * self.risk_per_trade
        return round(dollar_risk / price, 6)

    def record_loss(self, amount: float):
        self.daily_loss += amount
        self.consec_losses += 1
        if self.daily_loss <= self.max_daily_loss or self.consec_losses >= self.max_consec_losses:
            self.drawdown_triggered = True
            logging.warning("Drawdown or loss limit reached. Trading disabled.")

    def reset_daily_risk(self):
        self.daily_loss = 0.0
        self.consec_losses = 0
        self.drawdown_triggered = False
