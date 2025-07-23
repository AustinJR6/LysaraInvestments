from __future__ import annotations

"""In-memory cache of the latest ticker prices by symbol."""

from datetime import datetime
from typing import Dict

# key -> {'price': float, 'source': str, 'time': ISO8601}
_PRICE_CACHE: Dict[str, Dict[str, str | float]] = {}


def update_price(symbol: str, price: float, source: str) -> None:
    """Update cached price for a symbol.

    Parameters
    ----------
    symbol : str
        Canonical symbol like ``BTC-USD`` or ``AAPL``.
    price : float
        Latest trade/last price.
    source : str
        Data source identifier such as ``binance`` or ``alpaca``.
    """
    _PRICE_CACHE[symbol.upper()] = {
        "price": float(price),
        "source": source,
        "time": datetime.utcnow().isoformat(),
    }


def get_price(symbol: str) -> Dict[str, str | float] | None:
    """Return cached price entry for ``symbol`` if present."""
    return _PRICE_CACHE.get(symbol.upper())


def get_all() -> Dict[str, Dict[str, str | float]]:
    """Return the full cache."""
    return dict(_PRICE_CACHE)
