# dashboard/dashboard.py

import streamlit as st

from controls.trading_controls import show_trading_controls
from controls.risk_controls import show_risk_controls
from views.crypto_view import show_crypto_view
from views.stocks_view import show_stocks_view
from views.forex_view import show_forex_view
from utils.dashboard_helpers import load_control_flags


# Placeholder mock data
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

    st.title("🌐 Lysara Investments Dashboard")

    # Show sidebar controls
    show_trading_controls()
    show_risk_controls()

    # Load control flags (just to demonstrate usage)
    flags = load_control_flags()
    if flags:
        st.sidebar.markdown("### ⚙️ Active Flags")
        st.sidebar.json(flags)

    st.divider()

    # Display market tabs
    tabs = st.tabs(["📈 Crypto", "📊 Stocks", "💱 Forex"])

    with tabs[0]:
        show_crypto_view(mock_chart_data("crypto"))

    with tabs[1]:
        show_stocks_view(mock_chart_data("stocks"))

    with tabs[2]:
        show_forex_view(mock_chart_data("forex"))


if __name__ == "__main__":
    main()
