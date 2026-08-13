import json

import httpx
import pytest
import respx

from alchemy_wallet_client.exceptions import AlchemyRpcError
from alchemy_wallet_client.session_key import (
    ContractAccessPermission,
    Erc20TokenTransferPermission,
    FunctionsOnAllContractsPermission,
    FunctionsOnContractPermission,
    GasLimitPermission,
    InvalidSessionKeyError,
    NativeTokenTransferPermission,
    RootPermission,
    SessionKeyClient,
    SessionKeySigner,
    build_create_session_params,
    build_wallet_api_url,
    is_selector,
)
from alchemy_wallet_client.transport import JsonRpcTransport

VALID_ADDRESS = "0x1111111111111111111111111111111111111111"
VALID_TOKEN_ADDRESS = "0x2222222222222222222222222222222222222222"
VALID_SELECTOR = "0xa9059cbb"
URL = "https://api.g.alchemy.com/v2/test-key"

VALID_SIGNER = SessionKeySigner(public_key=VALID_ADDRESS)


def test_build_wallet_api_url() -> None:
    assert build_wallet_api_url("test-key") == URL


def test_is_selector_accepts_valid_selector() -> None:
    assert is_selector(VALID_SELECTOR) is True


@pytest.mark.parametrize("value", ["0xa9059c", "a9059cbb", "0xzzzzzzzz", "0x"])
def test_is_selector_rejects_invalid_values(value: str) -> None:
    assert is_selector(value) is False


# -- SessionKeySigner ---------------------------------------------------


def test_session_key_signer_to_dict_serializes_correctly() -> None:
    signer = SessionKeySigner(public_key=VALID_ADDRESS, key_type="ecdsa")

    assert signer.to_dict() == {"publicKey": VALID_ADDRESS, "type": "ecdsa"}


def test_session_key_signer_defaults_to_secp256k1() -> None:
    assert SessionKeySigner(public_key=VALID_ADDRESS).key_type == "secp256k1"


def test_session_key_signer_rejects_invalid_public_key() -> None:
    with pytest.raises(InvalidSessionKeyError):
        SessionKeySigner(public_key="not-an-address")


def test_session_key_signer_rejects_invalid_key_type() -> None:
    with pytest.raises(InvalidSessionKeyError):
        SessionKeySigner(public_key=VALID_ADDRESS, key_type="rsa")  # type: ignore[arg-type]


# -- Permission types -----------------------------------------------------


def test_root_permission_to_dict() -> None:
    assert RootPermission().to_dict() == {"type": "root"}


def test_contract_access_permission_to_dict() -> None:
    permission = ContractAccessPermission(address=VALID_ADDRESS)

    assert permission.to_dict() == {"type": "contract-access", "address": VALID_ADDRESS}


def test_contract_access_permission_rejects_invalid_address() -> None:
    with pytest.raises(InvalidSessionKeyError):
        ContractAccessPermission(address="not-an-address")


def test_functions_on_contract_permission_to_dict() -> None:
    permission = FunctionsOnContractPermission(address=VALID_ADDRESS, functions=(VALID_SELECTOR,))

    assert permission.to_dict() == {
        "type": "functions-on-contract",
        "address": VALID_ADDRESS,
        "functions": [VALID_SELECTOR],
    }


def test_functions_on_contract_permission_rejects_invalid_address() -> None:
    with pytest.raises(InvalidSessionKeyError):
        FunctionsOnContractPermission(address="not-an-address", functions=(VALID_SELECTOR,))


def test_functions_on_contract_permission_rejects_empty_functions() -> None:
    with pytest.raises(InvalidSessionKeyError):
        FunctionsOnContractPermission(address=VALID_ADDRESS, functions=())


def test_functions_on_contract_permission_rejects_invalid_selector() -> None:
    with pytest.raises(InvalidSessionKeyError):
        FunctionsOnContractPermission(address=VALID_ADDRESS, functions=("not-a-selector",))


def test_functions_on_all_contracts_permission_to_dict() -> None:
    permission = FunctionsOnAllContractsPermission(functions=(VALID_SELECTOR,))

    assert permission.to_dict() == {
        "type": "functions-on-all-contracts",
        "functions": [VALID_SELECTOR],
    }


def test_functions_on_all_contracts_permission_rejects_empty_functions() -> None:
    with pytest.raises(InvalidSessionKeyError):
        FunctionsOnAllContractsPermission(functions=())


def test_functions_on_all_contracts_permission_rejects_invalid_selector() -> None:
    with pytest.raises(InvalidSessionKeyError):
        FunctionsOnAllContractsPermission(functions=("not-a-selector",))


def test_native_token_transfer_permission_to_dict() -> None:
    permission = NativeTokenTransferPermission(allowance="0x1")

    assert permission.to_dict() == {"type": "native-token-transfer", "allowance": "0x1"}


@pytest.mark.parametrize("allowance", ["not-hex", "0x", ""])
def test_native_token_transfer_permission_rejects_invalid_allowance(allowance: str) -> None:
    with pytest.raises(InvalidSessionKeyError):
        NativeTokenTransferPermission(allowance=allowance)


def test_erc20_token_transfer_permission_to_dict() -> None:
    permission = Erc20TokenTransferPermission(address=VALID_TOKEN_ADDRESS, allowance="0x1")

    assert permission.to_dict() == {
        "type": "erc20-token-transfer",
        "address": VALID_TOKEN_ADDRESS,
        "allowance": "0x1",
    }


def test_erc20_token_transfer_permission_rejects_invalid_address() -> None:
    with pytest.raises(InvalidSessionKeyError):
        Erc20TokenTransferPermission(address="not-an-address", allowance="0x1")


@pytest.mark.parametrize("allowance", ["not-hex", "0x"])
def test_erc20_token_transfer_permission_rejects_invalid_allowance(allowance: str) -> None:
    with pytest.raises(InvalidSessionKeyError):
        Erc20TokenTransferPermission(address=VALID_TOKEN_ADDRESS, allowance=allowance)


def test_gas_limit_permission_to_dict() -> None:
    assert GasLimitPermission(limit="0x1").to_dict() == {"type": "gas-limit", "limit": "0x1"}


@pytest.mark.parametrize("limit", ["not-hex", "0x"])
def test_gas_limit_permission_rejects_invalid_limit(limit: str) -> None:
    with pytest.raises(InvalidSessionKeyError):
        GasLimitPermission(limit=limit)


# -- build_create_session_params ------------------------------------------


def test_build_create_session_params_includes_all_fields() -> None:
    permissions = [
        ContractAccessPermission(address=VALID_ADDRESS),
        Erc20TokenTransferPermission(address=VALID_TOKEN_ADDRESS, allowance="0x64"),
    ]

    params = build_create_session_params(
        account=VALID_ADDRESS,
        chain_id=8453,
        signer=VALID_SIGNER,
        permissions=permissions,
        expiry_sec=1_800_000_000,
    )

    assert params == {
        "account": VALID_ADDRESS,
        "chainId": hex(8453),
        "key": VALID_SIGNER.to_dict(),
        "permissions": [p.to_dict() for p in permissions],
        "expirySec": 1_800_000_000,
    }


def test_build_create_session_params_defaults_expiry_to_zero() -> None:
    params = build_create_session_params(
        account=VALID_ADDRESS,
        chain_id=1,
        signer=VALID_SIGNER,
        permissions=[RootPermission()],
    )

    assert params["expirySec"] == 0


def test_build_create_session_params_rejects_invalid_account() -> None:
    with pytest.raises(InvalidSessionKeyError):
        build_create_session_params(
            account="not-an-address",
            chain_id=1,
            signer=VALID_SIGNER,
            permissions=[RootPermission()],
        )


def test_build_create_session_params_rejects_non_positive_chain_id() -> None:
    with pytest.raises(InvalidSessionKeyError):
        build_create_session_params(
            account=VALID_ADDRESS,
            chain_id=0,
            signer=VALID_SIGNER,
            permissions=[RootPermission()],
        )


def test_build_create_session_params_rejects_empty_permissions() -> None:
    with pytest.raises(InvalidSessionKeyError):
        build_create_session_params(
            account=VALID_ADDRESS,
            chain_id=1,
            signer=VALID_SIGNER,
            permissions=[],
        )


def test_build_create_session_params_rejects_negative_expiry() -> None:
    with pytest.raises(InvalidSessionKeyError):
        build_create_session_params(
            account=VALID_ADDRESS,
            chain_id=1,
            signer=VALID_SIGNER,
            permissions=[RootPermission()],
            expiry_sec=-1,
        )


# -- SessionKeyClient -------------------------------------------------------


@pytest.fixture
def client() -> SessionKeyClient:
    transport = JsonRpcTransport(URL, backoff_factor=0)
    return SessionKeyClient(transport)


@respx.mock
def test_create_session_returns_result(client: SessionKeyClient) -> None:
    session_result = {
        "sessionId": "0xsessionid",
        "chainId": "0x2105",
        "signatureRequest": {
            "type": "eth_signTypedData_v4",
            "data": {"domain": {}, "types": {}, "primaryType": "DeferredAction", "message": {}},
            "rawPayload": "0xrawpayload",
        },
    }
    route = respx.post(URL).mock(
        return_value=httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": session_result})
    )

    result = client.create_session(
        account=VALID_ADDRESS,
        chain_id=8453,
        signer=VALID_SIGNER,
        permissions=[
            FunctionsOnContractPermission(address=VALID_ADDRESS, functions=(VALID_SELECTOR,)),
            NativeTokenTransferPermission(allowance="0x64"),
        ],
        expiry_sec=1_800_000_000,
    )

    assert result == session_result
    sent_body = json.loads(route.calls.last.request.content)
    assert sent_body["method"] == "wallet_createSession"
    assert sent_body["params"] == [
        {
            "account": VALID_ADDRESS,
            "chainId": hex(8453),
            "key": VALID_SIGNER.to_dict(),
            "permissions": [
                {
                    "type": "functions-on-contract",
                    "address": VALID_ADDRESS,
                    "functions": [VALID_SELECTOR],
                },
                {"type": "native-token-transfer", "allowance": "0x64"},
            ],
            "expirySec": 1_800_000_000,
        }
    ]
    client.close()


@respx.mock
def test_create_session_propagates_rpc_error(client: SessionKeyClient) -> None:
    respx.post(URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32000, "message": "account not found"},
            },
        )
    )

    with pytest.raises(AlchemyRpcError) as exc_info:
        client.create_session(
            account=VALID_ADDRESS,
            chain_id=1,
            signer=VALID_SIGNER,
            permissions=[RootPermission()],
        )

    assert exc_info.value.code == -32000
    client.close()


def test_context_manager_closes_transport() -> None:
    transport = JsonRpcTransport(URL, backoff_factor=0)
    with SessionKeyClient(transport):
        assert transport._client.is_closed is False
    assert transport._client.is_closed is True
