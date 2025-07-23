"""CryptoAPI now powered by :class:`BinanceClient`.

This thin wrapper preserves the previous ``CryptoAPI`` interface while
initialising ``BinanceClient`` with the new two-key strategy.  Callers may
still provide just ``api_key`` and ``secret_key`` for backward compatibility,
but the class will look for dedicated read/trade keys in the provided config if
available.
"""

from api.binance_client import BinanceClient


class CryptoAPI(BinanceClient):
    """Alias class for historical compatibility."""

    def __init__(
        self,
        api_key: str = "",
        secret_key: str = "",
        *,
        read_api_key: str | None = None,
        read_api_secret: str | None = None,
        trade_api_key: str | None = None,
        trade_api_secret: str | None = None,
        simulation_mode: bool = True,
        portfolio=None,
        config: dict | None = None,
        trade_cooldown: int = 30,
    ) -> None:
        config = config or {}
        api_cfg = config.get("api_keys", {})

        read_api_key = read_api_key or api_cfg.get("binance_read") or api_key
        read_api_secret = read_api_secret or api_cfg.get("binance_read_secret") or secret_key
        trade_api_key = trade_api_key or api_cfg.get("binance_trade") or api_key
        trade_api_secret = trade_api_secret or api_cfg.get("binance_trade_secret") or secret_key

        super().__init__(
            read_api_key=read_api_key,
            read_api_secret=read_api_secret,
            trade_api_key=trade_api_key,
            trade_api_secret=trade_api_secret,
            simulation_mode=simulation_mode,
            portfolio=portfolio,
            config=config,
            trade_cooldown=trade_cooldown,
        )

    async def fetch_holdings(self) -> dict:
        """Alias for ``get_holdings`` for backward compatibility."""
        return await self.get_holdings()

    async def close(self) -> None:
        """Alias for ``close`` to avoid attribute errors."""
        await super().close()
