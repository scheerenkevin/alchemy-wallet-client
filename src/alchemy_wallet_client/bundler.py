"""Bundler API client: ERC-4337 JSON-RPC method wrappers.

Covers the core UserOperation lifecycle methods needed to submit sponsored
transactions through an ERC-4337 bundler: estimate gas, send, and poll for
a receipt. See Alchemy's Bundler API docs for the full JSON-RPC method set;
this client wraps a `JsonRpcTransport` pointed at a chain-specific Bundler
endpoint (see the multi-chain configuration module for per-chain URLs).
"""

from __future__ import annotations

from typing import Any

from alchemy_wallet_client.transport import JsonRpcTransport

#: A UserOperation is a plain JSON-serializable mapping per the ERC-4337 spec
#: (sender, nonce, callData, signature, gas fields, etc.).
UserOperation = dict[str, Any]


class BundlerClient:
    """Thin wrapper over the Alchemy Bundler JSON-RPC API."""

    def __init__(self, transport: JsonRpcTransport) -> None:
        self._transport = transport

    def send_user_operation(self, user_operation: UserOperation, entry_point: str) -> str:
        """Submit a UserOperation for execution (`eth_sendUserOperation`).

        Args:
            user_operation: the UserOperation struct to submit.
            entry_point: address of the EntryPoint contract to target.

        Returns:
            The `userOpHash` identifying the submitted operation.
        """
        return self._transport.call("eth_sendUserOperation", params=[user_operation, entry_point])

    def estimate_user_operation_gas(
        self, user_operation: UserOperation, entry_point: str
    ) -> dict[str, Any]:
        """Estimate gas values for a UserOperation without submitting it
        (`eth_estimateUserOperationGas`).

        Returns:
            A mapping with the estimated gas fields (e.g.
            `preVerificationGas`, `verificationGasLimit`, `callGasLimit`).
        """
        return self._transport.call(
            "eth_estimateUserOperationGas", params=[user_operation, entry_point]
        )

    def get_user_operation_receipt(self, user_op_hash: str) -> dict[str, Any] | None:
        """Fetch the receipt for a previously submitted UserOperation
        (`eth_getUserOperationReceipt`).

        Returns:
            The receipt mapping, or `None` if the UserOperation has not
            been included in a block yet.
        """
        return self._transport.call("eth_getUserOperationReceipt", params=[user_op_hash])

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> BundlerClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
