"""Trading API utilities."""

# Coinbase trading support has been fully replaced by Binance.
# The old :mod:`coinbase_client` module is kept only for historical
# reference and should no longer be imported elsewhere.

from .binance_client import BinanceClient
from .coingecko_utils import get_price

__all__ = [
    "BinanceClient",
    "get_price",
]
