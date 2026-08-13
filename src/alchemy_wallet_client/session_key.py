"""Modular Account V2 session-key support: allowlisted, spend-limited,
time-boxed signers that can act on a smart account without full control.

Wraps Alchemy's Wallet API `wallet_createSession` JSON-RPC method — the
documented mechanism for installing a session key on a Modular Account V2
(allowlist specific contracts/methods, cap native/ERC-20 spend, set an
expiry) without a third-party ERC-7579 module, unlike Safe. See
`SessionKeyClient` and `build_create_session_params`.

This module does **not** perform cryptographic signing. `create_session`
returns a `signatureRequest` (EIP-712 typed data) that the account owner
must sign to activate the session; signing is the caller's responsibility,
consistent with the rest of this package (e.g. `smart_account.py`). Once a
session is active, UserOperations signed by the session key are ordinary
UserOperations — submit them through the existing `BundlerClient` unchanged,
no separate submission path is needed.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from alchemy_wallet_client.smart_account import is_address, is_hex
from alchemy_wallet_client.transport import JsonRpcTransport

_SELECTOR_RE = re.compile(r"^0x[0-9a-fA-F]{8}$")

_DEFAULT_WALLET_API_BASE = "https://api.g.alchemy.com"

#: The `type` field of the session key's own signer (the `key` param of
#: `wallet_createSession`).
SessionKeySignerType = Literal["secp256k1", "ecdsa", "contract"]

_SIGNER_TYPES: frozenset[str] = frozenset({"secp256k1", "ecdsa", "contract"})


class InvalidSessionKeyError(ValueError):
    """Raised when a session-key signer, permission, or request fails validation."""


def is_selector(value: str) -> bool:
    """Return True if `value` is a well-formed 4-byte hex function selector."""
    return bool(_SELECTOR_RE.match(value))


def build_wallet_api_url(api_key: str) -> str:
    """Build the Alchemy Wallet API URL used for `wallet_createSession` and
    other Smart Wallets JSON-RPC methods.

    Unlike the Bundler/Gas-Manager-sponsorship endpoint (see `chains.py`),
    this is not chain-scoped by URL — the target chain is passed as a
    `chainId` request param instead.
    """
    return f"{_DEFAULT_WALLET_API_BASE}/v2/{api_key}"


@dataclass(frozen=True)
class SessionKeySigner:
    """The signer to register as a session key (`key` param of
    `wallet_createSession`): its own address plus key type.
    """

    public_key: str
    key_type: SessionKeySignerType = "secp256k1"

    def __post_init__(self) -> None:
        if not is_address(self.public_key):
            raise InvalidSessionKeyError(
                f"public_key is not a valid 20-byte hex address: {self.public_key!r}"
            )
        if self.key_type not in _SIGNER_TYPES:
            raise InvalidSessionKeyError(f"key_type is not supported: {self.key_type!r}")

    def to_dict(self) -> dict[str, Any]:
        return {"publicKey": self.public_key, "type": self.key_type}


@dataclass(frozen=True)
class RootPermission:
    """Grants full, unscoped access to the account — the opposite of a
    scoped session key.

    Included for completeness of `wallet_createSession`'s documented
    permission surface. Almost never what a treasury/automation session
    key should use; prefer the allowlist/spend-limit permission types
    below to keep the session scoped.
    """

    def to_dict(self) -> dict[str, Any]:
        return {"type": "root"}


@dataclass(frozen=True)
class ContractAccessPermission:
    """Allows calling any function on a single allowlisted contract."""

    address: str

    def __post_init__(self) -> None:
        if not is_address(self.address):
            raise InvalidSessionKeyError(f"address is not a valid address: {self.address!r}")

    def to_dict(self) -> dict[str, Any]:
        return {"type": "contract-access", "address": self.address}


@dataclass(frozen=True)
class FunctionsOnContractPermission:
    """Allows calling only specific 4-byte function selectors on a single
    allowlisted contract.
    """

    address: str
    functions: tuple[str, ...]

    def __post_init__(self) -> None:
        if not is_address(self.address):
            raise InvalidSessionKeyError(f"address is not a valid address: {self.address!r}")
        if not self.functions:
            raise InvalidSessionKeyError("functions must not be empty.")
        for fn in self.functions:
            if not is_selector(fn):
                raise InvalidSessionKeyError(f"not a valid 4-byte function selector: {fn!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "functions-on-contract",
            "address": self.address,
            "functions": list(self.functions),
        }


@dataclass(frozen=True)
class FunctionsOnAllContractsPermission:
    """Allows calling specific 4-byte function selectors on any contract."""

    functions: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.functions:
            raise InvalidSessionKeyError("functions must not be empty.")
        for fn in self.functions:
            if not is_selector(fn):
                raise InvalidSessionKeyError(f"not a valid 4-byte function selector: {fn!r}")

    def to_dict(self) -> dict[str, Any]:
        return {"type": "functions-on-all-contracts", "functions": list(self.functions)}


@dataclass(frozen=True)
class NativeTokenTransferPermission:
    """Caps cumulative native-token (ETH, MATIC, ...) transfer/spend."""

    allowance: str

    def __post_init__(self) -> None:
        if not is_hex(self.allowance) or self.allowance == "0x":
            raise InvalidSessionKeyError(
                f"allowance must be a non-empty 0x-prefixed hex string: {self.allowance!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {"type": "native-token-transfer", "allowance": self.allowance}


@dataclass(frozen=True)
class Erc20TokenTransferPermission:
    """Caps cumulative ERC-20 transfer/approval spend for one token
    (a single allowance shared across all transfers and approvals, not a
    per-call limit).
    """

    address: str
    allowance: str

    def __post_init__(self) -> None:
        if not is_address(self.address):
            raise InvalidSessionKeyError(f"address is not a valid address: {self.address!r}")
        if not is_hex(self.allowance) or self.allowance == "0x":
            raise InvalidSessionKeyError(
                f"allowance must be a non-empty 0x-prefixed hex string: {self.allowance!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "erc20-token-transfer",
            "address": self.address,
            "allowance": self.allowance,
        }


@dataclass(frozen=True)
class GasLimitPermission:
    """Caps the gas the session key can spend on UserOperations."""

    limit: str

    def __post_init__(self) -> None:
        if not is_hex(self.limit) or self.limit == "0x":
            raise InvalidSessionKeyError(
                f"limit must be a non-empty 0x-prefixed hex string: {self.limit!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {"type": "gas-limit", "limit": self.limit}


#: Any of `wallet_createSession`'s documented permission types.
SessionKeyPermission = (
    RootPermission
    | ContractAccessPermission
    | FunctionsOnContractPermission
    | FunctionsOnAllContractsPermission
    | NativeTokenTransferPermission
    | Erc20TokenTransferPermission
    | GasLimitPermission
)


def build_create_session_params(
    *,
    account: str,
    chain_id: int,
    signer: SessionKeySigner,
    permissions: Sequence[SessionKeyPermission],
    expiry_sec: int = 0,
) -> dict[str, Any]:
    """Build the `params[0]` payload for `wallet_createSession`.

    Args:
        account: the Modular Account V2 address the session key is scoped to.
        chain_id: numeric chain id the session is valid on.
        signer: the session key's own signer (address + key type).
        permissions: the allowlist/spend-limit/expiry permission set to
            grant — at least one is required. Prefer the scoped permission
            types (`ContractAccessPermission`, `FunctionsOnContractPermission`,
            `Erc20TokenTransferPermission`, etc.) over `RootPermission` for
            anything but full-control automation.
        expiry_sec: unix timestamp the session expires at, or 0 for no
            expiry (matching `wallet_createSession`'s own convention).

    Returns:
        A JSON-serializable mapping — pass it directly as
        `wallet_createSession`'s `params[0]`, which `SessionKeyClient.create_session`
        does for you.
    """
    if not is_address(account):
        raise InvalidSessionKeyError(f"account is not a valid address: {account!r}")
    if chain_id <= 0:
        raise InvalidSessionKeyError("chain_id must be > 0.")
    if not permissions:
        raise InvalidSessionKeyError("permissions must not be empty.")
    if expiry_sec < 0:
        raise InvalidSessionKeyError("expiry_sec must be >= 0 (0 means no expiry).")

    return {
        "account": account,
        "chainId": hex(chain_id),
        "key": signer.to_dict(),
        "permissions": [permission.to_dict() for permission in permissions],
        "expirySec": expiry_sec,
    }


class SessionKeyClient:
    """Thin wrapper over Alchemy's Wallet API session-key JSON-RPC method(s)."""

    def __init__(self, transport: JsonRpcTransport) -> None:
        self._transport = transport

    def create_session(
        self,
        *,
        account: str,
        chain_id: int,
        signer: SessionKeySigner,
        permissions: Sequence[SessionKeyPermission],
        expiry_sec: int = 0,
    ) -> dict[str, Any]:
        """Create a session key on a Modular Account V2 (`wallet_createSession`).

        Returns:
            A mapping with `sessionId` and a `signatureRequest` (EIP-712
            typed data) that the account owner must sign to activate the
            session. Signing is the caller's responsibility. Once active,
            UserOperations signed by `signer` are ordinary UserOperations:
            submit them through `BundlerClient.send_user_operation`
            unchanged, no separate method is needed.
        """
        params = build_create_session_params(
            account=account,
            chain_id=chain_id,
            signer=signer,
            permissions=permissions,
            expiry_sec=expiry_sec,
        )
        return self._transport.call("wallet_createSession", params=[params])

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> SessionKeyClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
