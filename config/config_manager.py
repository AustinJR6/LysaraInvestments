# ==============================
# config/config_manager.py
# ==============================

import os
import json
from dotenv import load_dotenv
from pathlib import Path

class ConfigManager:
    def __init__(self):
        load_dotenv()
        self.base_config = {}

    def load_config(self):
        self.load_env_vars()
        self.load_json_config()
        self.load_asset_specific_configs()
        return self.base_config

    def load_env_vars(self):
        self.base_config['api_keys'] = {
            'coinbase': os.getenv('COINBASE_API_KEY'),
            'coinbase_secret': os.getenv('COINBASE_SECRET_KEY'),
            'alpaca': os.getenv('ALPACA_API_KEY'),
            'alpaca_secret': os.getenv('ALPACA_SECRET_KEY'),
            'alpaca_base_url': os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets'),
            'newsapi': os.getenv('NEWSAPI_KEY'),
            'cryptopanic': os.getenv('CRYPTOPANIC_KEY'),
            'slack_webhook': os.getenv('SLACK_WEBHOOK_URL'),
            'openai': os.getenv('OPENAI_API_KEY'),
        }
        self.base_config['simulation_mode'] = os.getenv('SIMULATION_MODE', 'True').lower() in ('true', '1', 'yes')
        self.base_config['ENABLE_STOCK_TRADING'] = os.getenv('ENABLE_STOCK_TRADING', 'false').lower() in ('true', '1', 'yes')
        self.base_config['ENABLE_AI_STRATEGY'] = os.getenv('ENABLE_AI_STRATEGY', 'false').lower() in ('true', '1', 'yes')
        self.base_config['ENABLE_AI_ASSET_DISCOVERY'] = os.getenv('ENABLE_AI_ASSET_DISCOVERY', 'false').lower() in ('true', '1', 'yes')
        self.base_config['LIVE_TRADING_ENABLED'] = os.getenv('LIVE_TRADING_ENABLED', 'true').lower() in ('true', '1', 'yes')
        self.base_config['log_level'] = os.getenv('LOG_LEVEL', 'INFO')
        self.base_config['db_path'] = os.getenv('DB_PATH', 'trades.db')
        self.base_config['config_path'] = os.getenv('CONFIG_PATH', 'config.json')
        self.base_config['log_file_path'] = os.getenv('LOG_FILE_PATH', 'trading_bot.log')
        self.base_config['TRADE_SYMBOLS'] = os.getenv('TRADE_SYMBOLS', '')

    def load_json_config(self):
        path = self.base_config.get('config_path', 'config.json')
        if Path(path).is_file():
            try:
                with open(path, 'r') as f:
                    self.base_config.update(json.load(f))
            except json.JSONDecodeError:
                print(f"Error: Could not decode {path}.")
        else:
            print(f"Warning: {path} not found. Using default settings.")

    def load_asset_specific_configs(self):
        self.base_config['crypto_settings'] = self._load_json('config/settings_crypto.json')
        self.base_config['stocks_settings'] = self._load_json('config/settings_stocks.json')
        self.base_config['forex_settings'] = self._load_json('config/settings_forex.json')

    def _load_json(self, filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"Warning: Failed to load or parse {filepath}. Returning empty dict.")
            return {}
