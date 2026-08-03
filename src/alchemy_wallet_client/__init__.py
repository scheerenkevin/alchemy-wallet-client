"""alchemy_wallet_client.

Python client for Alchemy's server-side wallet / account-abstraction stack:
the Bundler API (ERC-4337 JSON-RPC methods) and the Gas Manager API (REST
Admin API + JSON-RPC sponsorship methods).

This is an unofficial, community client — Alchemy ships an official
TypeScript SDK but no official Python SDK.
"""

from alchemy_wallet_client.config import (
    DEFAULT_API_KEY_ENV_VAR,
    AlchemyConfig,
    MissingApiKeyError,
)

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_API_KEY_ENV_VAR",
    "AlchemyConfig",
    "MissingApiKeyError",
    "__version__",
]
