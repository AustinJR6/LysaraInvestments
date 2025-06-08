# main.py

import sys
import asyncio
if sys.platform.startswith("win"):
    from asyncio import WindowsSelectorEventLoopPolicy
    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

import logging
from config.config_manager import ConfigManager
from utils.logger import setup_logging
from services.bot_launcher import BotLauncher

async def main():
    config = ConfigManager().load_config()

    setup_logging(
        level=config.get("log_level", "INFO"),
        log_file_path=config.get("log_file_path", "logs/trading_bot.log")
    )

    logging.info("Lysara Investments booting up...")
    logging.info(
        f"Simulation mode: {config.get('simulation_mode', True)} | Risk per trade: {config.get('crypto_settings', {}).get('risk_per_trade')}"
    )

    launcher = BotLauncher(config)
    launcher.start_all_bots()

    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.warning("Shutdown requested. Exiting gracefully.")
