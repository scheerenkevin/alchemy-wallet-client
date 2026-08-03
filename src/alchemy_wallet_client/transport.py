"""Core JSON-RPC-over-HTTP transport used by the Bundler and Gas Manager
Sponsorship API clients.

Handles request/response (de)serialization, JSON-RPC vs. HTTP-level error
mapping, and retries with exponential backoff for transient failures.
"""

from __future__ import annotations

import itertools
import time
from types import TracebackType
from typing import Any

import httpx

from alchemy_wallet_client.exceptions import (
    AlchemyHttpError,
    AlchemyRpcError,
    AlchemyTimeoutError,
)
from alchemy_wallet_client.models import JsonRpcParams, JsonRpcRequest, JsonRpcResponse

#: HTTP status codes considered transient and worth retrying.
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

_DEFAULT_TIMEOUT = 30.0
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BACKOFF_FACTOR = 0.5


class JsonRpcTransport:
    """Sends JSON-RPC 2.0 requests over HTTP with retries.

    One transport instance targets a single URL (e.g. a specific chain's
    Bundler or Gas Manager sponsorship endpoint). Construct one per
    endpoint/chain as needed.
    """

    def __init__(
        self,
        url: str,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        backoff_factor: float = _DEFAULT_BACKOFF_FACTOR,
        client: httpx.Client | None = None,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        self._url = url
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None
        self._id_counter = itertools.count(1)

    def call(self, method: str, params: JsonRpcParams = None) -> Any:
        """Send a single JSON-RPC method call and return its `result`.

        Raises:
            AlchemyRpcError: the server returned a JSON-RPC error object.
            AlchemyHttpError: a non-retryable (or retries-exhausted) HTTP
                failure occurred, or the response body was not valid JSON.
            AlchemyTimeoutError: the request timed out after all retries.
        """
        request = JsonRpcRequest(method=method, params=params, id=next(self._id_counter))
        response = self._send_with_retries(request)

        if response.error is not None:
            raise AlchemyRpcError(
                response.error.message, code=response.error.code, data=response.error.data
            )
        return response.result

    def _send_with_retries(self, request: JsonRpcRequest) -> JsonRpcResponse:
        attempt = 0

        while True:
            try:
                http_response = self._client.post(self._url, json=request.to_dict())
            except httpx.TimeoutException as exc:
                if attempt >= self._max_retries:
                    raise AlchemyTimeoutError(
                        f"Request to {self._url} timed out after {attempt + 1} attempt(s)."
                    ) from exc
                self._sleep(attempt)
                attempt += 1
                continue
            except httpx.TransportError as exc:
                if attempt >= self._max_retries:
                    raise AlchemyHttpError(
                        f"Request to {self._url} failed after {attempt + 1} attempt(s): {exc}"
                    ) from exc
                self._sleep(attempt)
                attempt += 1
                continue

            if http_response.status_code in _RETRYABLE_STATUS_CODES:
                if attempt >= self._max_retries:
                    raise AlchemyHttpError(
                        f"Request to {self._url} failed with status "
                        f"{http_response.status_code} after {attempt + 1} attempt(s).",
                        status_code=http_response.status_code,
                    )
                self._sleep(attempt)
                attempt += 1
                continue

            if http_response.status_code >= 400:
                raise AlchemyHttpError(
                    f"Request to {self._url} failed with status {http_response.status_code}.",
                    status_code=http_response.status_code,
                )

            try:
                body = http_response.json()
            except ValueError as exc:
                raise AlchemyHttpError(f"Response from {self._url} was not valid JSON.") from exc

            return JsonRpcResponse.from_dict(body)

    def _sleep(self, attempt: int) -> None:
        if self._backoff_factor <= 0:
            return
        time.sleep(self._backoff_factor * (2**attempt))

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> JsonRpcTransport:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
