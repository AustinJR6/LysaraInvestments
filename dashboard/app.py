# dashboard/app.py

"""Main entry for the Streamlit dashboard with real-time updates."""

import streamlit as st

from controls.trading_controls import show_trading_controls
from controls.risk_controls import show_risk_controls
from views import (
    show_crypto_view,
    show_stocks_view,
    show_forex_view,
    show_trade_history,
    show_performance_view,
    show_log_view,
    show_portfolio_table,
    show_sim_summary,
)
from utils import (
    load_control_flags,
    auto_refresh,
    get_last_trade,
    get_trade_history,
    get_performance_metrics,
    get_equity,
    get_log_lines,
    get_sentiment_data,
    mock_trade_history,
    PortfolioManager,
)
from config.config_manager import ConfigManager


# Placeholder chart data for markets

def mock_chart_data(label: str):
    import pandas as pd
    import numpy as np
    import datetime

    now = datetime.datetime.now()
    return [
        {"time": (now - datetime.timedelta(minutes=i)).isoformat(), "price": 100 + np.sin(i / 3) * 5}
        for i in range(60)
    ]


def main():
    st.set_page_config(page_title="Lysara Dashboard", layout="wide")

    auto_refresh(10)

    st.title("🌐 Lysara Investments Dashboard")

    # Sidebar controls
    show_trading_controls()
    show_risk_controls()

    flags = load_control_flags()
    if flags:
        st.sidebar.markdown("### ⚙️ Active Flags")
        st.sidebar.json(flags)

    st.divider()

    config = ConfigManager().load_config()
    pm = PortfolioManager(config)

    last_trade = get_last_trade()
    trade_history = get_trade_history()
    metrics = get_performance_metrics()
    equity = get_equity()
    sentiment = get_sentiment_data()
    logs = get_log_lines()

    real_holdings = pm.get_account_holdings()
    sim_data = pm.get_simulated_portfolio() if config.get("simulation_mode", True) else None

    if not trade_history:
        trade_history = mock_trade_history()

    top = st.columns(3)
    if last_trade:
        top[0].write(
            f"**Last Trade:** {last_trade['timestamp']} {last_trade['symbol']} {last_trade['side']} {last_trade['quantity']} @ {last_trade['price']} PnL={last_trade['pnl']}"
        )
    else:
        top[0].write("**Last Trade:** None")

    top[1].metric("Portfolio Equity", equity)
    top[2].metric("Open Risk", metrics.get("open_risk", 0.0))

    holdings_tabs = st.tabs([
        "💰 Simulated Holdings",
        "📊 Real Crypto",
        "📈 Real Stocks",
        "🌍 Real Forex",
    ])

    with holdings_tabs[0]:
        if sim_data:
            show_portfolio_table(sim_data.get("positions", []), "Simulated Holdings")
            show_sim_summary(sim_data.get("summary", {}), sim_data.get("balance", 0.0))
        else:
            st.info("Simulation mode disabled or no data available.")

    with holdings_tabs[1]:
        crypto_positions = real_holdings.get("crypto", [])
        if crypto_positions:
            show_portfolio_table(crypto_positions, "Crypto Account Holdings")
        else:
            st.info("No real holdings available.")

    with holdings_tabs[2]:
        stock_positions = real_holdings.get("stocks", [])
        if stock_positions:
            show_portfolio_table(stock_positions, "Stock Account Holdings")
        else:
            st.info("No real holdings available.")

    with holdings_tabs[3]:
        forex_positions = real_holdings.get("forex", [])
        if forex_positions:
            show_portfolio_table(forex_positions, "Forex Account Holdings")
        else:
            st.info("No real holdings available.")

    st.divider()

    market_tabs = st.tabs([
        "📈 Crypto",
        "📊 Stocks",
        "💱 Forex",
        "📜 Trades",
        "📊 Performance",
        "📝 Logs",
    ])

    with market_tabs[0]:
        show_crypto_view(mock_chart_data("crypto"))
    with market_tabs[1]:
        show_stocks_view(mock_chart_data("stocks"))
    with market_tabs[2]:
        show_forex_view(mock_chart_data("forex"))
    with market_tabs[3]:
        show_trade_history(trade_history)
    with market_tabs[4]:
        show_performance_view(metrics)
    with market_tabs[5]:
        show_log_view(logs)

    if sentiment:
        st.sidebar.markdown("### 🗣 Sentiment Scores")
        st.sidebar.json(sentiment)


if __name__ == "__main__":
    main()
