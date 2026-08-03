"""Gas Manager Sponsorship API client: JSON-RPC paymaster sponsorship
methods.

Separate surface from the Gas Manager Admin (REST) API — these are
JSON-RPC methods (e.g. `alchemy_requestGasAndPaymasterAndData`) called
against a chain's Alchemy RPC endpoint, used to obtain paymaster data and
gas estimates so a UserOperation can be submitted sponsored via the
Bundler API.
"""

from __future__ import annotations

from typing import Any

from alchemy_wallet_client.transport import JsonRpcTransport

#: A UserOperation is a plain JSON-serializable mapping per the ERC-4337 spec.
UserOperation = dict[str, Any]


class GasManagerSponsorshipClient:
    """Thin wrapper over Alchemy's Gas Manager JSON-RPC sponsorship methods."""

    def __init__(self, transport: JsonRpcTransport) -> None:
        self._transport = transport

    def request_gas_and_paymaster_and_data(
        self,
        *,
        policy_id: str,
        entry_point: str,
        user_operation: UserOperation,
        dummy_signature: str | None = None,
    ) -> dict[str, Any]:
        """Request sponsorship (paymaster data + gas estimates) for a
        UserOperation (`alchemy_requestGasAndPaymasterAndData`).

        Args:
            policy_id: the Gas Manager policy id to sponsor under.
            entry_point: address of the EntryPoint contract to target.
            user_operation: the (partial) UserOperation to get sponsorship for.
            dummy_signature: optional placeholder signature to use for gas
                estimation before the real signature is available.

        Returns:
            A mapping with the paymaster-related fields and gas estimates
            to merge into the UserOperation before signing and submitting
            it via `BundlerClient.send_user_operation`.
        """
        params: dict[str, Any] = {
            "policyId": policy_id,
            "entryPoint": entry_point,
            "userOperation": user_operation,
        }
        if dummy_signature is not None:
            params["dummySignature"] = dummy_signature
        return self._transport.call("alchemy_requestGasAndPaymasterAndData", params=[params])

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> GasManagerSponsorshipClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
