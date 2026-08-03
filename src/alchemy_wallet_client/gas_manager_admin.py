"""Gas Manager Admin API client (REST): policy management.

Wraps Alchemy's Gas Manager Admin REST API used to create, read, update,
list, and delete Gas Manager sponsorship policies. This is a separate
surface from the JSON-RPC sponsorship methods (see
`gas_manager_sponsorship.py`) — the Admin API is plain REST, authenticated
with a bearer auth token rather than an app API key in the URL.
"""

from __future__ import annotations

import time
from types import TracebackType
from typing import Any

import httpx

from alchemy_wallet_client.exceptions import AlchemyHttpError, AlchemyTimeoutError

#: HTTP status codes considered transient and worth retrying.
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

_DEFAULT_BASE_URL = "https://manage.g.alchemy.com"
_DEFAULT_TIMEOUT = 30.0
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BACKOFF_FACTOR = 0.5

#: A Gas Manager policy is a plain JSON-serializable mapping.
Policy = dict[str, Any]


class GasManagerAdminClient:
    """REST client for Alchemy's Gas Manager Admin API (policy management)."""

    def __init__(
        self,
        auth_token: str,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        backoff_factor: float = _DEFAULT_BACKOFF_FACTOR,
        client: httpx.Client | None = None,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._client = client or httpx.Client(
            timeout=timeout,
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        self._owns_client = client is None

    def create_policy(self, policy: Policy) -> Policy:
        """Create a new Gas Manager sponsorship policy."""
        return self._request("POST", "/api/gasManager/policy", json=policy)

    def get_policy(self, policy_id: str) -> Policy:
        """Fetch a single policy by id."""
        return self._request("GET", f"/api/gasManager/policy/{policy_id}")

    def list_policies(self) -> list[Policy]:
        """List all policies for the authenticated team."""
        result = self._request("GET", "/api/gasManager/policies")
        if isinstance(result, dict):
            return result.get("data", [])
        return result

    def update_policy(self, policy_id: str, updates: Policy) -> Policy:
        """Partially update an existing policy."""
        return self._request("PATCH", f"/api/gasManager/policy/{policy_id}", json=updates)

    def delete_policy(self, policy_id: str) -> None:
        """Delete a policy by id."""
        self._request("DELETE", f"/api/gasManager/policy/{policy_id}")

    def _request(self, method: str, path: str, *, json: Any = None) -> Any:
        url = f"{self._base_url}{path}"
        attempt = 0

        while True:
            try:
                response = self._client.request(method, url, json=json)
            except httpx.TimeoutException as exc:
                if attempt >= self._max_retries:
                    raise AlchemyTimeoutError(
                        f"Request to {url} timed out after {attempt + 1} attempt(s)."
                    ) from exc
                self._sleep(attempt)
                attempt += 1
                continue
            except httpx.TransportError as exc:
                if attempt >= self._max_retries:
                    raise AlchemyHttpError(
                        f"Request to {url} failed after {attempt + 1} attempt(s): {exc}"
                    ) from exc
                self._sleep(attempt)
                attempt += 1
                continue

            if response.status_code in _RETRYABLE_STATUS_CODES:
                if attempt >= self._max_retries:
                    raise AlchemyHttpError(
                        f"Request to {url} failed with status {response.status_code} "
                        f"after {attempt + 1} attempt(s).",
                        status_code=response.status_code,
                    )
                self._sleep(attempt)
                attempt += 1
                continue

            if response.status_code >= 400:
                raise AlchemyHttpError(
                    f"Request to {url} failed with status {response.status_code}: {response.text}",
                    status_code=response.status_code,
                )

            if response.status_code == 204 or not response.content:
                return None

            try:
                return response.json()
            except ValueError as exc:
                raise AlchemyHttpError(f"Response from {url} was not valid JSON.") from exc

    def _sleep(self, attempt: int) -> None:
        if self._backoff_factor <= 0:
            return
        time.sleep(self._backoff_factor * (2**attempt))

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> GasManagerAdminClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
