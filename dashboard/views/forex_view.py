# dashboard/views/forex_view.py

import streamlit as st
import pandas as pd

def show_forex_view(data):
    """
    Display forex-related market data in chart format.
    Expects data to be a list of dicts with 'time' and 'price' keys.
    """
    st.header("💱 Forex Market Overview")

    if not data:
        st.write("No forex market data available.")
        return

    try:
        df = pd.DataFrame(data)
        df['time'] = pd.to_datetime(df['time'])
        df = df.set_index('time')
        st.line_chart(df['price'])
    except Exception as e:
        st.error(f"Failed to render forex chart: {e}")
