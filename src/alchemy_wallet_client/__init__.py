"""alchemy_wallet_client.

Python client for Alchemy's server-side wallet / account-abstraction stack:
the Bundler API (ERC-4337 JSON-RPC methods) and the Gas Manager API (REST
Admin API + JSON-RPC sponsorship methods).

This is an unofficial, community client — Alchemy ships an official
TypeScript SDK but no official Python SDK.
"""

from alchemy_wallet_client.bundler import BundlerClient
from alchemy_wallet_client.chains import SUPPORTED_CHAINS, Chain, build_rpc_url, get_chain_by_id
from alchemy_wallet_client.config import (
    DEFAULT_API_KEY_ENV_VAR,
    AlchemyConfig,
    MissingApiKeyError,
)
from alchemy_wallet_client.exceptions import (
    AlchemyError,
    AlchemyHttpError,
    AlchemyRpcError,
    AlchemyTimeoutError,
)
from alchemy_wallet_client.gas_manager_admin import GasManagerAdminClient
from alchemy_wallet_client.gas_manager_sponsorship import GasManagerSponsorshipClient
from alchemy_wallet_client.smart_account import (
    Eip7702Authorization,
    InvalidAuthorizationError,
    InvalidUserOperationError,
    build_eip7702_user_operation,
    merge_sponsorship_result,
)
from alchemy_wallet_client.transport import JsonRpcTransport

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_API_KEY_ENV_VAR",
    "SUPPORTED_CHAINS",
    "AlchemyConfig",
    "AlchemyError",
    "AlchemyHttpError",
    "AlchemyRpcError",
    "AlchemyTimeoutError",
    "BundlerClient",
    "Chain",
    "Eip7702Authorization",
    "GasManagerAdminClient",
    "GasManagerSponsorshipClient",
    "InvalidAuthorizationError",
    "InvalidUserOperationError",
    "JsonRpcTransport",
    "MissingApiKeyError",
    "build_eip7702_user_operation",
    "build_rpc_url",
    "get_chain_by_id",
    "merge_sponsorship_result",
    "__version__",
]
