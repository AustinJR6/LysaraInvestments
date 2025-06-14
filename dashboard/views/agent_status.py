import streamlit as st
from typing import Dict


def show_agent_status(info: Dict, auto_mode: bool = True):
    """Display the latest agent decision."""
    status = "ON" if auto_mode else "OFF"
    st.header(f"🤖 Agent Status ({status})")
    if not info:
        st.info("No agent activity yet.")
        return
    decision = info.get("decision", {})
    st.write(f"Time: {info.get('timestamp')}")
    st.write(f"Action: {decision.get('action')}")
    st.write(f"Confidence: {decision.get('confidence')}")
    st.write(f"Rationale: {decision.get('rationale') or decision.get('reason')}")
