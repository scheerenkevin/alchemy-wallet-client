"""EIP-7702 / smart-account helper utilities.

These helpers build and validate the plain-dict payloads used by the
`BundlerClient` and `GasManagerSponsorshipClient` for EIP-7702-compatible
smart accounts (an EOA that temporarily delegates code execution to a
smart-contract implementation via a signed authorization).

This module does **not** perform cryptographic signing — signing
UserOperations and EIP-7702 authorizations is the caller's responsibility
(e.g. via `eth_account` or KeeperOS's own key management), consistent with
this package being an HTTP client rather than a wallet/signing library.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from alchemy_wallet_client.bundler import UserOperation

_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
_HEX_RE = re.compile(r"^0x[0-9a-fA-F]*$")


class InvalidAuthorizationError(ValueError):
    """Raised when an EIP-7702 authorization tuple fails validation."""


class InvalidUserOperationError(ValueError):
    """Raised when a UserOperation payload fails validation."""


def is_address(value: str) -> bool:
    """Return True if `value` is a well-formed 20-byte hex address."""
    return bool(_ADDRESS_RE.match(value))


def is_hex(value: str) -> bool:
    """Return True if `value` is a well-formed 0x-prefixed hex string."""
    return bool(_HEX_RE.match(value))


@dataclass(frozen=True)
class Eip7702Authorization:
    """A signed EIP-7702 authorization tuple.

    Permits `address`'s code to be executed from the signing EOA on
    `chain_id` (0 meaning "any chain"), at the given `nonce`, per the
    signature `(y_parity, r, s)`. Validated on construction.
    """

    chain_id: int
    address: str
    nonce: int
    y_parity: int
    r: str
    s: str

    def __post_init__(self) -> None:
        if self.chain_id < 0:
            raise InvalidAuthorizationError("chain_id must be >= 0 (0 means any chain).")
        if not is_address(self.address):
            raise InvalidAuthorizationError(
                f"address is not a valid 20-byte hex address: {self.address!r}"
            )
        if self.nonce < 0:
            raise InvalidAuthorizationError("nonce must be >= 0.")
        if self.y_parity not in (0, 1):
            raise InvalidAuthorizationError("y_parity must be 0 or 1.")
        if not is_hex(self.r) or not is_hex(self.s):
            raise InvalidAuthorizationError("r and s must be 0x-prefixed hex strings.")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the shape expected in an `authorizationList` entry
        of an EIP-7702 transaction / UserOperation.
        """
        return {
            "chainId": hex(self.chain_id),
            "address": self.address,
            "nonce": hex(self.nonce),
            "yParity": hex(self.y_parity),
            "r": self.r,
            "s": self.s,
        }


def build_eip7702_user_operation(
    *,
    sender: str,
    nonce: str,
    call_data: str,
    authorization: Eip7702Authorization,
    call_gas_limit: str | None = None,
    verification_gas_limit: str | None = None,
    pre_verification_gas: str | None = None,
    max_fee_per_gas: str | None = None,
    max_priority_fee_per_gas: str | None = None,
    signature: str = "0x",
) -> UserOperation:
    """Build a UserOperation payload for an EIP-7702-delegated smart
    account, ready to pass to `GasManagerSponsorshipClient` for
    gas/paymaster estimation and then `BundlerClient.send_user_operation`
    once signed.

    Only `sender`, `nonce`, `callData`, `signature`, and
    `authorizationList` are always populated; gas fields are optional here
    since they are typically filled in later from
    `estimate_user_operation_gas` / sponsorship responses via
    `merge_sponsorship_result`.
    """
    if not is_address(sender):
        raise InvalidUserOperationError(f"sender is not a valid address: {sender!r}")
    if not is_hex(call_data):
        raise InvalidUserOperationError(f"call_data must be 0x-prefixed hex: {call_data!r}")

    user_op: UserOperation = {
        "sender": sender,
        "nonce": nonce,
        "callData": call_data,
        "signature": signature,
        "authorizationList": [authorization.to_dict()],
    }
    optional_fields = {
        "callGasLimit": call_gas_limit,
        "verificationGasLimit": verification_gas_limit,
        "preVerificationGas": pre_verification_gas,
        "maxFeePerGas": max_fee_per_gas,
        "maxPriorityFeePerGas": max_priority_fee_per_gas,
    }
    for key, value in optional_fields.items():
        if value is not None:
            user_op[key] = value
    return user_op


def merge_sponsorship_result(
    user_operation: UserOperation, sponsorship_result: dict[str, Any]
) -> UserOperation:
    """Merge a Gas Manager sponsorship response (paymaster data, gas
    estimates) into a UserOperation.

    Returns a new dict; does not mutate either input.
    """
    return {**user_operation, **sponsorship_result}
