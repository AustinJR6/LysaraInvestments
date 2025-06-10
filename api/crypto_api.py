"""Backward compatible CryptoAPI using Coinbase Advanced Trade SDK."""

from api.coinbase_client import CoinbaseClient


class CryptoAPI(CoinbaseClient):
    """Alias class for historical compatibility."""

    def __init__(
        self,
        api_key: str,
        secret_key: str = "",
        passphrase: str | None = None,
        simulation_mode: bool = True,
        portfolio=None,
        config: dict | None = None,
        trade_cooldown: int = 30,
    ) -> None:
        super().__init__(
            api_key=api_key,
            api_secret=secret_key,
            simulation_mode=simulation_mode,
            portfolio=portfolio,
            config=config,
            trade_cooldown=trade_cooldown,
        )
