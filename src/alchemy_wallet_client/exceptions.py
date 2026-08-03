"""Exception hierarchy for alchemy_wallet_client.

All exceptions raised by this library's HTTP/JSON-RPC layers derive from
`AlchemyError`, so callers can catch broadly (`except AlchemyError`) or
narrowly (`except AlchemyRpcError`) as needed.
"""

from __future__ import annotations

from typing import Any


class AlchemyError(Exception):
    """Base class for all errors raised by alchemy_wallet_client."""


class AlchemyHttpError(AlchemyError):
    """Raised when an HTTP request fails at the transport level.

    Covers non-2xx responses (after retries are exhausted) that are not a
    well-formed JSON-RPC error body, and any other HTTP-layer failure.
    """

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AlchemyTimeoutError(AlchemyError):
    """Raised when a request times out after all retries are exhausted."""


class AlchemyRpcError(AlchemyError):
    """Raised when a JSON-RPC response contains an `error` object.

    Mirrors the JSON-RPC 2.0 error object: `code`, `message`, and optional
    `data`.
    """

    def __init__(self, message: str, *, code: int, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.data = data

    def __repr__(self) -> str:
        return f"AlchemyRpcError(code={self.code}, message={str(self)!r}, data={self.data!r})"
