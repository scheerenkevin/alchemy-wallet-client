import json

import httpx
import pytest
import respx

from alchemy_wallet_client.bundler import BundlerClient
from alchemy_wallet_client.exceptions import AlchemyRpcError
from alchemy_wallet_client.transport import JsonRpcTransport

URL = "https://base-mainnet.g.alchemy.com/v2/test-key"
ENTRY_POINT = "0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789"
USER_OP: dict[str, object] = {
    "sender": "0x11111111111111111111111111111111111111",
    "nonce": "0x0",
    "callData": "0xdeadbeef",
    "signature": "0x",
}


@pytest.fixture
def client() -> BundlerClient:
    transport = JsonRpcTransport(URL, backoff_factor=0)
    return BundlerClient(transport)


@respx.mock
def test_send_user_operation_returns_hash(client: BundlerClient) -> None:
    route = respx.post(URL).mock(
        return_value=httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": "0xuserophash"})
    )

    result = client.send_user_operation(USER_OP, ENTRY_POINT)

    assert result == "0xuserophash"
    sent_body = json.loads(route.calls.last.request.content)
    assert sent_body["method"] == "eth_sendUserOperation"
    assert sent_body["params"] == [USER_OP, ENTRY_POINT]
    client.close()


@respx.mock
def test_estimate_user_operation_gas_returns_estimates(client: BundlerClient) -> None:
    estimates = {
        "preVerificationGas": "0x1",
        "verificationGasLimit": "0x2",
        "callGasLimit": "0x3",
    }
    route = respx.post(URL).mock(
        return_value=httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": estimates})
    )

    result = client.estimate_user_operation_gas(USER_OP, ENTRY_POINT)

    assert result == estimates
    sent_body = json.loads(route.calls.last.request.content)
    assert sent_body["method"] == "eth_estimateUserOperationGas"
    assert sent_body["params"] == [USER_OP, ENTRY_POINT]
    client.close()


@respx.mock
def test_get_user_operation_receipt_returns_receipt(client: BundlerClient) -> None:
    receipt = {"userOpHash": "0xuserophash", "success": True}
    route = respx.post(URL).mock(
        return_value=httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": receipt})
    )

    result = client.get_user_operation_receipt("0xuserophash")

    assert result == receipt
    sent_body = json.loads(route.calls.last.request.content)
    assert sent_body["method"] == "eth_getUserOperationReceipt"
    assert sent_body["params"] == ["0xuserophash"]
    client.close()


@respx.mock
def test_get_user_operation_receipt_returns_none_when_not_found(client: BundlerClient) -> None:
    respx.post(URL).mock(
        return_value=httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": None})
    )

    result = client.get_user_operation_receipt("0xnotfoundyet")

    assert result is None
    client.close()


@respx.mock
def test_send_user_operation_propagates_rpc_error(client: BundlerClient) -> None:
    respx.post(URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32500, "message": "AA21 didn't pay prefund"},
            },
        )
    )

    with pytest.raises(AlchemyRpcError) as exc_info:
        client.send_user_operation(USER_OP, ENTRY_POINT)

    assert exc_info.value.code == -32500
    client.close()


def test_context_manager_closes_transport() -> None:
    transport = JsonRpcTransport(URL, backoff_factor=0)
    with BundlerClient(transport):
        assert transport._client.is_closed is False
    assert transport._client.is_closed is True
