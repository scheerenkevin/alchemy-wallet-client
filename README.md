# alchemy-wallet-client

> **This repo is a read-only push-mirror** from
> [Forgejo](https://git.cubealgos.de/kevin/alchemy-wallet-client), the real
> source of truth. Issues are closed here; open them on the forge instead.
> `pip install git+https://github.com/...` still works fine — this is only
> about where development happens.

Python client for Alchemy's server-side wallet / account-abstraction stack: the
**Bundler API** (ERC-4337 JSON-RPC methods) and the **Gas Manager API** (REST Admin
API + JSON-RPC sponsorship methods).

## Why this exists

Alchemy ships an official TypeScript SDK for its wallet/account-abstraction stack,
but no official Python SDK. Both the Bundler API and Gas Manager API are JSON-RPC/REST
under the hood, so this package wraps them directly over HTTP with `httpx` — a typed
Python interface over Alchemy's existing public API surface, not a reimplementation of
undocumented behavior.

## Relationship to evm_automation

This package is consumed by **evm_automation** (`evm_automation`), an autonomous DeFi keeper
platform, as its executor-wallet dependency: EIP-7702-compatible smart accounts,
submitting sponsored transactions across Base (primary), Ethereum, Arbitrum, Optimism,
Polygon, BNB Chain, and Avalanche C-Chain. Alchemy is already evm_automation's RPC provider,
so this consolidates on one vendor instead of adding a separate wallet-infra vendor
(Coinbase CDP, Circle, Turnkey, etc. were evaluated and rejected for this reason).

## Installation

This project uses [Hatch](https://hatch.pypa.io/) for packaging and targets Python 3.12+.

```bash
git clone https://github.com/scheerenkevin/alchemy-wallet-client.git
cd alchemy-wallet-client
pip install -e .
```

For local development (lint, format, tests):

```bash
hatch env create
hatch run lint
hatch run format
hatch run test
```

## Authentication

Set your Alchemy API key in an environment variable — it is never hardcoded or logged:

```bash
export ALCHEMY_API_KEY="your-alchemy-api-key"
```

```python
from alchemy_wallet_client import AlchemyConfig

config = AlchemyConfig.from_env()  # reads ALCHEMY_API_KEY; raises MissingApiKeyError if unset
```

## Usage

### Multi-chain configuration

```python
from alchemy_wallet_client import Chain, build_rpc_url

url = build_rpc_url(Chain.BASE, config.api_key)
# "https://base-mainnet.g.alchemy.com/v2/your-alchemy-api-key"
```

`Chain` covers all seven chains evm_automation operates on: `BASE`, `ETHEREUM`, `ARBITRUM`,
`OPTIMISM`, `POLYGON`, `BNB_CHAIN`, `AVALANCHE` (see the table below).

### Sending a UserOperation via the Bundler API

```python
from alchemy_wallet_client import BundlerClient, JsonRpcTransport, Chain, build_rpc_url

transport = JsonRpcTransport(build_rpc_url(Chain.BASE, config.api_key))
bundler = BundlerClient(transport)

entry_point = "0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789"
user_op = {
    "sender": "0xYourSmartAccountAddress",
    "nonce": "0x0",
    "callData": "0x...",
    "signature": "0x...",
}

gas_estimate = bundler.estimate_user_operation_gas(user_op, entry_point)
user_op_hash = bundler.send_user_operation(user_op, entry_point)
receipt = bundler.get_user_operation_receipt(user_op_hash)  # None until included in a block

bundler.close()
```

### Requesting sponsorship via the Gas Manager Sponsorship API

```python
from alchemy_wallet_client import GasManagerSponsorshipClient, JsonRpcTransport

sponsorship = GasManagerSponsorshipClient(
    JsonRpcTransport(build_rpc_url(Chain.BASE, config.api_key))
)

result = sponsorship.request_gas_and_paymaster_and_data(
    policy_id="your-gas-manager-policy-id",
    entry_point=entry_point,
    user_operation=user_op,
)
# result contains paymasterAndData + gas estimates to merge into user_op

sponsorship.close()
```

### Managing Gas Manager policies (Admin API)

The Admin API is a separate REST surface (bearer-token auth) from the JSON-RPC
sponsorship methods above:

```python
from alchemy_wallet_client import GasManagerAdminClient

admin = GasManagerAdminClient(auth_token="your-gas-manager-admin-auth-token")

policy = admin.create_policy(
    {
        "policyName": "evm_automation-base-sponsorship",
        "rules": {"maxSpendUsd": "100"},
    }
)
policies = admin.list_policies()
admin.update_policy(policy["id"], {"status": "active"})

admin.close()
```

### EIP-7702 smart-account UserOperations

This package builds and validates UserOperation/authorization *payloads* — it does not
perform cryptographic signing. Signing is the caller's responsibility (e.g. via
`eth_account` or evm_automation's own key management).

```python
from alchemy_wallet_client import (
    Eip7702Authorization,
    build_eip7702_user_operation,
    merge_sponsorship_result,
)

authorization = Eip7702Authorization(
    chain_id=8453,
    address="0xYourSmartAccountImplementation",
    nonce=0,
    y_parity=1,
    r="0x...",  # produced by signing the authorization elsewhere
    s="0x...",
)

user_op = build_eip7702_user_operation(
    sender="0xYourEoaAddress",
    nonce="0x0",
    call_data="0x...",
    authorization=authorization,
)

sponsorship_result = sponsorship.request_gas_and_paymaster_and_data(
    policy_id="your-gas-manager-policy-id",
    entry_point=entry_point,
    user_operation=user_op,
)
user_op = merge_sponsorship_result(user_op, sponsorship_result)
# ... sign user_op["signature"] ...
user_op_hash = bundler.send_user_operation(user_op, entry_point)
```

### Error handling

All errors derive from `AlchemyError`:

```python
from alchemy_wallet_client import (
    AlchemyError,
    AlchemyRpcError,
    AlchemyHttpError,
    AlchemyTimeoutError,
)

try:
    bundler.send_user_operation(user_op, entry_point)
except AlchemyRpcError as e:
    print(e.code, str(e), e.data)  # a well-formed JSON-RPC error from Alchemy
except AlchemyHttpError as e:
    print(e.status_code, str(e))  # non-retryable HTTP failure, or retries exhausted
except AlchemyTimeoutError as e:
    print(str(e))  # timed out after all retries
except AlchemyError as e:
    ...  # catch-all
```

`JsonRpcTransport`, `GasManagerAdminClient`, and `GasManagerSponsorshipClient` all
retry transient failures (429/500/502/503/504, connection errors, timeouts) with
exponential backoff, and never retry non-retryable 4xx errors.

## Supported chains

| Chain               | Chain ID | Alchemy network   |
| ------------------- | -------- | ----------------- |
| Base (primary)       | 8453     | `base-mainnet`    |
| Ethereum             | 1        | `eth-mainnet`     |
| Arbitrum             | 42161    | `arb-mainnet`     |
| Optimism             | 10       | `opt-mainnet`     |
| Polygon              | 137      | `polygon-mainnet` |
| BNB Chain            | 56       | `bnb-mainnet`     |
| Avalanche C-Chain    | 43114    | `avax-mainnet`    |

## Development

This repo follows GitFlow (`main` / `develop` / `feature/*` / `release/*` / `hotfix/*`),
Conventional Commits, and issue-tracked work — see the
[Issues](../../issues) and [Project board](../../projects) for current status and the
full backlog.

```bash
hatch run lint      # ruff check
hatch run format    # ruff format
hatch run test      # pytest, respx-mocked HTTP — no live API calls anywhere
```

CI runs lint/format-check/test on every PR, a dev build on merges to `develop`, and an
automated SemVer release (tag + `CHANGELOG.md` update) on merges to `main`.

## License

MIT — see [LICENSE](LICENSE).
