import json
from pathlib import Path
import streamlit as st

LOG_PATH = "logs/agent_history.json"


def _load_last_entry():
    path = Path(LOG_PATH)
    if not path.is_file():
        return None
    try:
        line = path.read_text().strip().splitlines()[-1]
        return json.loads(line)
    except Exception:
        return None


def show_agent_status():
    st.header("🤖 Agent Status")
    auto = st.session_state.get("autonomous", True)
    st.checkbox("Autonomous Mode", value=auto, key="autonomous")

    info = _load_last_entry()
    if not info:
        st.info("No agent activity yet.")
        return

    st.subheader(f"Last decision for {info['ticker']}")
    st.write(f"Price: {info['price']}")
    st.write(f"Decision: {info['decision'].get('action')}")
    st.write(f"Confidence: {info['decision'].get('confidence')}")
    st.write(f"Rationale: {info['decision'].get('rationale')}")
    st.write(info['decision'].get('explanation'))

    if st.session_state.get("pending_trade"):
        col1, col2 = st.columns(2)
        if col1.button("Approve Trade"):
            st.session_state["pending_trade"] = False
        if col2.button("Reject Trade"):
            st.session_state["pending_trade"] = False
