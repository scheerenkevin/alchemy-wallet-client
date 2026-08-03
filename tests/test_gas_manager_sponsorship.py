import json

import httpx
import pytest
import respx

from alchemy_wallet_client.exceptions import AlchemyRpcError
from alchemy_wallet_client.gas_manager_sponsorship import GasManagerSponsorshipClient
from alchemy_wallet_client.transport import JsonRpcTransport

URL = "https://base-mainnet.g.alchemy.com/v2/test-key"
ENTRY_POINT = "0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789"
USER_OP: dict[str, object] = {
    "sender": "0x11111111111111111111111111111111111111",
    "nonce": "0x0",
    "callData": "0xdeadbeef",
}


@pytest.fixture
def client() -> GasManagerSponsorshipClient:
    transport = JsonRpcTransport(URL, backoff_factor=0)
    return GasManagerSponsorshipClient(transport)


@respx.mock
def test_request_gas_and_paymaster_and_data_returns_result(
    client: GasManagerSponsorshipClient,
) -> None:
    sponsorship_result = {
        "paymasterAndData": "0xpaymasterdata",
        "preVerificationGas": "0x1",
        "verificationGasLimit": "0x2",
        "callGasLimit": "0x3",
    }
    route = respx.post(URL).mock(
        return_value=httpx.Response(
            200, json={"jsonrpc": "2.0", "id": 1, "result": sponsorship_result}
        )
    )

    result = client.request_gas_and_paymaster_and_data(
        policy_id="policy-1",
        entry_point=ENTRY_POINT,
        user_operation=USER_OP,
    )

    assert result == sponsorship_result
    sent_body = json.loads(route.calls.last.request.content)
    assert sent_body["method"] == "alchemy_requestGasAndPaymasterAndData"
    assert sent_body["params"] == [
        {"policyId": "policy-1", "entryPoint": ENTRY_POINT, "userOperation": USER_OP}
    ]
    client.close()


@respx.mock
def test_request_includes_dummy_signature_when_provided(
    client: GasManagerSponsorshipClient,
) -> None:
    route = respx.post(URL).mock(
        return_value=httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {}})
    )

    client.request_gas_and_paymaster_and_data(
        policy_id="policy-1",
        entry_point=ENTRY_POINT,
        user_operation=USER_OP,
        dummy_signature="0xdeadbeef",
    )

    sent_body = json.loads(route.calls.last.request.content)
    assert sent_body["params"][0]["dummySignature"] == "0xdeadbeef"
    client.close()


@respx.mock
def test_omits_dummy_signature_when_not_provided(client: GasManagerSponsorshipClient) -> None:
    route = respx.post(URL).mock(
        return_value=httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {}})
    )

    client.request_gas_and_paymaster_and_data(
        policy_id="policy-1", entry_point=ENTRY_POINT, user_operation=USER_OP
    )

    sent_body = json.loads(route.calls.last.request.content)
    assert "dummySignature" not in sent_body["params"][0]
    client.close()


@respx.mock
def test_propagates_rpc_error(client: GasManagerSponsorshipClient) -> None:
    respx.post(URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32000, "message": "policy not found"},
            },
        )
    )

    with pytest.raises(AlchemyRpcError) as exc_info:
        client.request_gas_and_paymaster_and_data(
            policy_id="missing-policy", entry_point=ENTRY_POINT, user_operation=USER_OP
        )

    assert exc_info.value.code == -32000
    client.close()


def test_context_manager_closes_transport() -> None:
    transport = JsonRpcTransport(URL, backoff_factor=0)
    with GasManagerSponsorshipClient(transport):
        assert transport._client.is_closed is False
    assert transport._client.is_closed is True
