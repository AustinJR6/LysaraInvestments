# dashboard/views/crypto_view.py

import streamlit as st
import pandas as pd

def show_crypto_view(data):
    """
    Display crypto-related market data in a simple chart format.
    Expects data to be a list of dicts with 'time' and 'price' keys.
    """
    st.header("📈 Crypto Market Overview")

    if not data:
        st.write("No crypto market data available.")
        return

    try:
        df = pd.DataFrame(data)
        df['time'] = pd.to_datetime(df['time'])
        df = df.set_index('time')
        st.line_chart(df['price'])
    except Exception as e:
        st.error(f"Failed to render crypto chart: {e}")
