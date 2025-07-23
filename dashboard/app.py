# dashboard/app.py

"""Main entry for the Streamlit dashboard with real-time updates."""

import os
import sys

# Ensure the project root is on the Python path when running this file
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import streamlit as st
import datetime

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
    show_conviction_heatmap,
    show_ai_thought_feed,
    show_equity_curve,
    show_agent_status,
)
from dashboard.utils import (
    load_control_flags,
    auto_refresh,
    get_last_trade,
    get_last_trade_per_market,
    get_trade_history,
    get_performance_metrics,
    get_equity,
    get_equity_curve,
    get_log_lines,
    get_sentiment_data,
    get_ai_thoughts,
    get_last_agent_decision,
    mock_trade_history,
    PortfolioManager,
)
from config.config_manager import ConfigManager
from services.ai_strategist import get_last_decision


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

    config = ConfigManager().load_config()
    pm = PortfolioManager(config)
    forex_enabled = config.get("FOREX_ENABLED", False)

    mode = "LIVE" if not config.get("simulation_mode", True) else "SIM"
    banner_color = "red" if mode == "LIVE" else "green"
    st.markdown(
        f"<div style='background-color:{banner_color};padding:6px;text-align:center;color:white;'>Trading Mode: {mode}</div>",
        unsafe_allow_html=True,
    )

    if mode == "SIM":
        st.sidebar.success("✅ SIMULATION MODE ON")
    else:
        st.sidebar.error("❌ LIVE MODE ACTIVE")

    # Sidebar controls
    if config.get("SHOW_MANUAL_TRADING_UI", False):
        show_trading_controls(pm.sim_portfolio)
        show_risk_controls()

    flags = load_control_flags()
    if flags:
        st.sidebar.markdown("### ⚙️ Active Flags")
        st.sidebar.json(flags)

    auto_mode = st.sidebar.checkbox("Autonomous Mode", value=True)

    st.divider()


    with st.spinner("Loading data..."):
        try:
            last_trade = get_last_trade()
            trade_history = get_trade_history()
            metrics = get_performance_metrics()
            equity = get_equity()
            equity_curve_data = get_equity_curve()
            sentiment = get_sentiment_data()
            logs = get_log_lines()
            ai_feed = get_ai_thoughts()
            real_holdings = pm.get_account_holdings()
            sim_data = pm.get_simulated_portfolio() if config.get("simulation_mode", True) else None
        except Exception as e:
            st.error(f"Data load failed: {e}")
            last_trade = None
            trade_history = []
            metrics = {}
            equity = 0.0
            equity_curve_data = []
            sentiment = {}
            logs = []
            ai_feed = []
            real_holdings = {"crypto": [], "stocks": [], "forex": []}
            sim_data = None
    last_updated = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

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

    decision = get_last_decision()
    if decision:
        conf = decision["decision"].get("confidence", 0.0)
        color = "green" if conf >= 0.7 else "yellow" if conf >= 0.4 else "red"
        st.markdown("### AI Strategist Last Decision")
        st.markdown(
            f"<span style='background-color:{color};color:white;padding:4px;border-radius:3px'>{decision['decision'].get('action')} ({conf:.2f})</span> - {decision['decision'].get('reason','')}",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("### AI Strategist Last Decision")
        st.write("No decision logged yet.")

    agent_info = get_last_agent_decision()
    show_agent_status(agent_info, auto_mode)

    portfolio_tabs = st.tabs([
        "Simulated Portfolio",
        "Real Holdings",
        "Last Trades",
        "Trade History Summary",
    ])

    with portfolio_tabs[0]:
        if sim_data:
            show_portfolio_table(sim_data.get("positions", []), "Simulated Holdings")
            show_sim_summary(sim_data.get("summary", {}), sim_data.get("balance", 0.0))
        else:
            st.info("Simulation mode disabled or no data available.")
        st.caption(f"Last Updated: {last_updated} UTC")

    with portfolio_tabs[1]:
        tabs = ["Crypto", "Stocks"]
        if forex_enabled:
            tabs.append("Forex")
        real_tabs = st.tabs(tabs)
        with real_tabs[0]:
            crypto_positions = real_holdings.get("crypto", [])
            if crypto_positions:
                show_portfolio_table(crypto_positions, "Crypto Account Holdings")
            else:
                st.info("No real holdings available.")
        with real_tabs[1]:
            stock_positions = real_holdings.get("stocks", [])
            if stock_positions:
                show_portfolio_table(stock_positions, "Stock Account Holdings")
            else:
                st.info("No real holdings available.")
        if forex_enabled and len(real_tabs) > 2:
            with real_tabs[2]:
                forex_positions = real_holdings.get("forex", [])
                if forex_positions:
                    show_portfolio_table(forex_positions, "Forex Account Holdings")
                else:
                    st.info("No real holdings available.")
        st.caption(f"Last Updated: {last_updated} UTC")

    with portfolio_tabs[2]:
        last_trades = get_last_trade_per_market()
        markets = ["crypto", "stocks"]
        if forex_enabled:
            markets.append("forex")
        for market_label in markets:
            trade = last_trades.get(market_label)
            st.subheader(market_label.capitalize())
            if trade:
                st.write(
                    f"{trade['timestamp']} {trade['symbol']} {trade['side']} {trade['quantity']} @ {trade['price']} confidence={trade.get('reason','')}"
                )
            else:
                st.write("No trades yet.")
        st.caption(f"Last Updated: {last_updated} UTC")

    with portfolio_tabs[3]:
        show_trade_history(trade_history)
        show_performance_view(metrics)
        st.caption(f"Last Updated: {last_updated} UTC")

    st.divider()

    tab_list = ["Crypto Chart", "Stocks Chart"]
    if forex_enabled:
        tab_list.append("Forex Chart")
    tab_list.extend(["Equity Curve", "AI Feed", "Heatmap", "Logs"])
    log_tabs = st.tabs(tab_list)
    idx = 0
    with log_tabs[idx]:
        show_crypto_view(mock_chart_data("crypto"))
    idx += 1
    with log_tabs[idx]:
        show_stocks_view(mock_chart_data("stocks"))
    idx += 1
    if forex_enabled:
        with log_tabs[idx]:
            show_forex_view(mock_chart_data("forex"))
        idx += 1
    with log_tabs[idx]:
        show_equity_curve(equity_curve_data)
    idx += 1
    with log_tabs[idx]:
        show_ai_thought_feed(ai_feed)
    idx += 1
    with log_tabs[idx]:
        show_conviction_heatmap(sentiment)
    idx += 1
    with log_tabs[idx]:
        show_log_view(logs)

    if sentiment:
        st.sidebar.markdown("### 🗣 Sentiment Scores")
        st.sidebar.write(
            "Sources: " + ", ".join(sorted(sentiment.keys()))
        )
        st.sidebar.json(sentiment)


if __name__ == "__main__":
    main()
