"""Multi-chain configuration: chain IDs and per-chain Alchemy RPC URL
construction for the chains evm_automation operates on — Base (primary),
Ethereum, Arbitrum, Optimism, Polygon, BNB Chain, and Avalanche C-Chain.

Alchemy exposes both the standard `eth_*` JSON-RPC methods and the
Bundler/Gas-Manager-sponsorship JSON-RPC methods on the same per-chain RPC
endpoint (`https://<network-slug>.g.alchemy.com/v2/<api-key>`), so this
module only needs to build one URL per chain. The Gas Manager Admin (REST)
API is not chain-scoped by URL (see `gas_manager_admin.py`).

Network slugs verified against Alchemy's RPC directory (alchemy.com/rpc).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Chain(Enum):
    """Chains supported by this client, identified by a stable key."""

    BASE = "base"
    ETHEREUM = "ethereum"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    POLYGON = "polygon"
    BNB_CHAIN = "bnb-chain"
    AVALANCHE = "avalanche"


@dataclass(frozen=True)
class ChainInfo:
    """Static metadata for a chain: numeric chain id and Alchemy network slug."""

    chain: Chain
    chain_id: int
    alchemy_network: str


_CHAIN_INFO: dict[Chain, ChainInfo] = {
    Chain.BASE: ChainInfo(Chain.BASE, chain_id=8453, alchemy_network="base-mainnet"),
    Chain.ETHEREUM: ChainInfo(Chain.ETHEREUM, chain_id=1, alchemy_network="eth-mainnet"),
    Chain.ARBITRUM: ChainInfo(Chain.ARBITRUM, chain_id=42161, alchemy_network="arb-mainnet"),
    Chain.OPTIMISM: ChainInfo(Chain.OPTIMISM, chain_id=10, alchemy_network="opt-mainnet"),
    Chain.POLYGON: ChainInfo(Chain.POLYGON, chain_id=137, alchemy_network="polygon-mainnet"),
    Chain.BNB_CHAIN: ChainInfo(Chain.BNB_CHAIN, chain_id=56, alchemy_network="bnb-mainnet"),
    Chain.AVALANCHE: ChainInfo(Chain.AVALANCHE, chain_id=43114, alchemy_network="avax-mainnet"),
}

_CHAIN_ID_TO_CHAIN: dict[int, Chain] = {info.chain_id: chain for chain, info in _CHAIN_INFO.items()}


def get_chain_info(chain: Chain) -> ChainInfo:
    """Look up static metadata (chain id, Alchemy network slug) for a chain."""
    return _CHAIN_INFO[chain]


def get_chain_by_id(chain_id: int) -> Chain:
    """Reverse-lookup a `Chain` from its numeric chain id.

    Raises:
        KeyError: if `chain_id` is not one of the supported chains.
    """
    try:
        return _CHAIN_ID_TO_CHAIN[chain_id]
    except KeyError as exc:
        raise KeyError(f"Unsupported chain id: {chain_id}") from exc


def build_rpc_url(chain: Chain, api_key: str) -> str:
    """Build the Alchemy RPC URL for `chain`.

    This single endpoint serves standard `eth_*` methods, Bundler API
    methods (`eth_sendUserOperation`, etc.), and Gas Manager sponsorship
    methods (`alchemy_requestGasAndPaymasterAndData`).
    """
    info = get_chain_info(chain)
    return f"https://{info.alchemy_network}.g.alchemy.com/v2/{api_key}"


#: All supported chains, in the order evm_automation prioritizes them (Base first).
SUPPORTED_CHAINS: tuple[Chain, ...] = (
    Chain.BASE,
    Chain.ETHEREUM,
    Chain.ARBITRUM,
    Chain.OPTIMISM,
    Chain.POLYGON,
    Chain.BNB_CHAIN,
    Chain.AVALANCHE,
)
