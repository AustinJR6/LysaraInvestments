import logging
import os
from pathlib import Path
from typing import Optional

from onchain_agent.initialize_agent import initialize_agent


def _load_private_key(path: Path) -> Optional[str]:
    try:
        key = path.read_text().strip()
        logging.info(f"Loaded PEM key from {path}")
        return key
    except FileNotFoundError:
        logging.error(f"Private key file not found at {path}")
    except Exception as exc:
        logging.error(f"Failed to load PEM key: {exc}")
    return None


def launch_agent(test: bool = False):
    """Load configuration and start the onchain agent."""
    pem_path = Path("secrets/coinbase_private_key.pem")
    private_key = _load_private_key(pem_path)
    if not private_key:
        return

    cdp_api_key = os.getenv("CDP_API_KEY")
    chain_id = os.getenv("CHAIN_ID")
    rpc_url = os.getenv("RPC_URL")

    missing = [
        name
        for name, val in [
            ("CDP_API_KEY", cdp_api_key),
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
        initialize_agent(private_key, cdp_api_key, chain_id_int, rpc_url, test=test)
    except Exception as exc:
        logging.error(f"Agent initialization failed: {exc}")
        return
