"""CryptoAPI now powered by BinanceClient for trading."""

from api.binance_client import BinanceClient


class CryptoAPI(BinanceClient):
    """Alias class for historical compatibility."""

    def __init__(
        self,
        api_key: str,
        secret_key: str = "",
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

    async def fetch_holdings(self) -> dict:
        """Alias for ``get_holdings`` for backward compatibility."""
        return await self.get_holdings()

    async def close(self) -> None:
        """Alias for ``close`` to avoid attribute errors."""
        await super().close()
