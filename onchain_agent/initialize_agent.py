import logging
from typing import Tuple

from web3 import Web3
from eth_account import Account
from coinbase_agentkit.agentkit import AgentKit, AgentKitConfig


def initialize_agent(
    private_key_pem: str,
    cdp_api_key: str,
    chain_id: int,
    rpc_url: str,
    test: bool = False,
) -> Tuple[AgentKit, Web3, str]:
    """Initialize the onchain agent and return useful objects.

    Parameters
    ----------
    private_key_pem : str
        PEM-formatted private key text.
    cdp_api_key : str
        Coinbase Developer Platform API key.
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

    try:
        account = Account.from_key(private_key_pem)
    except Exception as exc:
        raise ValueError(f"Invalid private key: {exc}") from exc

    config = AgentKitConfig(cdp_api_key_id=cdp_api_key)
    agent = AgentKit(config)

    logging.info(f"Agent wallet address: {account.address}")
    logging.info(f"Connected to RPC {rpc_url}")
    return agent, w3, account.address
