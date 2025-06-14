from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any


@dataclass
class MarketSnapshot:
    ticker: str
    price: float
    sentiment: Dict[str, Any]
    technicals: Dict[str, Any]
    volatility: float
    timestamp: datetime
