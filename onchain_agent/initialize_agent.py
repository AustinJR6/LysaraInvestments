import logging
import os
from typing import Tuple

from web3 import Web3
from coinbase_agentkit.agentkit import AgentKit, AgentKitConfig


def initialize_agent(
    cdp_api_key: str,
    cdp_project_id: str,
    chain_id: int,
    rpc_url: str,
    test: bool = False,
) -> Tuple[AgentKit, Web3, str]:
    """Initialize the onchain agent and return useful objects.

    Parameters
    ----------
    cdp_api_key : str
        Coinbase Developer Platform API key.
    cdp_project_id : str
        Coinbase Developer Platform project id.
    chain_id : int
        Target chain id.
    rpc_url : str
        RPC endpoint for the chain.
    test : bool, optional
        If True, skip RPC connectivity checks.
    """
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not test and not w3.is_connected():
        raise ValueError("Unable to connect to RPC endpoint")

    os.environ.setdefault("CDP_API_KEY", cdp_api_key)
    os.environ.setdefault("CDP_PROJECT_ID", cdp_project_id)

    agent = AgentKit(AgentKitConfig())
    wallet_address = agent.wallet_provider.get_address()

    logging.info(f"Agent wallet address: {wallet_address}")
    logging.info(f"Connected to RPC {rpc_url}")
    return agent, w3, wallet_address
