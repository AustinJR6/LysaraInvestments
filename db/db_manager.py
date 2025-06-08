# db/db_manager.py

import sqlite3
import logging
from db.models.trades import create_trades_table, insert_trade
from db.models.orders import create_orders_table, insert_order
from db.models.equity_snapshots import create_equity_table, insert_equity_snapshot

class DatabaseManager:
    def __init__(self, db_path: str = "trades.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._initialize_tables()

    def _initialize_tables(self):
        logging.info("Initializing database tables...")
        create_trades_table(self.conn)
        create_orders_table(self.conn)
        create_equity_table(self.conn)

    def log_trade(self, **kwargs):
        try:
            insert_trade(self.conn, **kwargs)
            logging.info(f"Trade logged: {kwargs}")
        except Exception as e:
            logging.error(f"Failed to log trade: {e}")

    def log_order(self, **kwargs):
        try:
            insert_order(self.conn, **kwargs)
            logging.info(f"Order logged: {kwargs}")
        except Exception as e:
            logging.error(f"Failed to log order: {e}")

    def log_equity_snapshot(self, equity: float, market: str):
        try:
            insert_equity_snapshot(self.conn, equity, market)
            logging.info(f"Equity snapshot logged: {equity} ({market})")
        except Exception as e:
            logging.error(f"Failed to log equity snapshot: {e}")

    def close(self):
        self.conn.close()
        logging.info("Database connection closed.")
