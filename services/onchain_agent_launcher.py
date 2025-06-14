import logging
import os

from onchain_agent.initialize_agent import initialize_agent

def launch_agent(test: bool = False):
    """Load configuration and start the onchain agent."""

    cdp_api_key = os.getenv("CDP_API_KEY")
    cdp_project_id = os.getenv("CDP_PROJECT_ID")
    chain_id = os.getenv("CHAIN_ID")
    rpc_url = os.getenv("RPC_URL")

    missing = [
        name
        for name, val in [
            ("CDP_API_KEY", cdp_api_key),
            ("CDP_PROJECT_ID", cdp_project_id),
            ("CHAIN_ID", chain_id),
            ("RPC_URL", rpc_url),
        ]
        if not val
    ]
    if missing:
        logging.error(f"Missing required env vars: {', '.join(missing)}")
        return

    try:
        chain_id_int = int(chain_id)
    except ValueError:
        logging.error("CHAIN_ID must be an integer")
        return

    try:
        initialize_agent(cdp_api_key, cdp_project_id, chain_id_int, rpc_url, test=test)
    except Exception as exc:
        logging.error(f"Agent initialization failed: {exc}")
        return
