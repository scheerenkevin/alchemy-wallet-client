import httpx
import pytest
import respx

from alchemy_wallet_client.exceptions import (
    AlchemyHttpError,
    AlchemyRpcError,
    AlchemyTimeoutError,
)
from alchemy_wallet_client.transport import JsonRpcTransport

URL = "https://example.alchemy.com/v2/test-key"


@respx.mock
def test_call_returns_result_on_success() -> None:
    respx.post(URL).mock(
        return_value=httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": "0xabc"})
    )
    transport = JsonRpcTransport(URL, backoff_factor=0)

    result = transport.call("eth_sendUserOperation", params=["0x1", "0x2"])

    assert result == "0xabc"
    transport.close()


@respx.mock
def test_call_raises_rpc_error() -> None:
    respx.post(URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32602, "message": "invalid params", "data": {"foo": "bar"}},
            },
        )
    )
    transport = JsonRpcTransport(URL, backoff_factor=0)

    with pytest.raises(AlchemyRpcError) as exc_info:
        transport.call("eth_sendUserOperation")

    assert exc_info.value.code == -32602
    assert exc_info.value.data == {"foo": "bar"}
    assert "invalid params" in str(exc_info.value)
    transport.close()


@respx.mock
def test_retries_on_5xx_then_succeeds() -> None:
    route = respx.post(URL)
    route.side_effect = [
        httpx.Response(503),
        httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": "ok"}),
    ]
    transport = JsonRpcTransport(URL, backoff_factor=0, max_retries=3)

    result = transport.call("eth_getUserOperationReceipt", params=["0xhash"])

    assert result == "ok"
    assert route.call_count == 2
    transport.close()


@respx.mock
def test_raises_http_error_after_retries_exhausted() -> None:
    respx.post(URL).mock(return_value=httpx.Response(500))
    transport = JsonRpcTransport(URL, backoff_factor=0, max_retries=2)

    with pytest.raises(AlchemyHttpError) as exc_info:
        transport.call("eth_estimateUserOperationGas")

    assert exc_info.value.status_code == 500
    transport.close()


@respx.mock
def test_no_retry_on_4xx_client_error() -> None:
    route = respx.post(URL).mock(return_value=httpx.Response(400, json={"error": "bad request"}))
    transport = JsonRpcTransport(URL, backoff_factor=0, max_retries=5)

    with pytest.raises(AlchemyHttpError) as exc_info:
        transport.call("eth_sendUserOperation")

    assert exc_info.value.status_code == 400
    assert route.call_count == 1
    transport.close()


@respx.mock
def test_raises_timeout_error_after_retries_exhausted() -> None:
    respx.post(URL).mock(side_effect=httpx.TimeoutException("timed out"))
    transport = JsonRpcTransport(URL, backoff_factor=0, max_retries=1)

    with pytest.raises(AlchemyTimeoutError):
        transport.call("eth_sendUserOperation")

    transport.close()


@respx.mock
def test_raises_http_error_on_transport_error_after_retries() -> None:
    respx.post(URL).mock(side_effect=httpx.ConnectError("connection refused"))
    transport = JsonRpcTransport(URL, backoff_factor=0, max_retries=1)

    with pytest.raises(AlchemyHttpError):
        transport.call("eth_sendUserOperation")

    transport.close()


@respx.mock
def test_raises_http_error_on_invalid_json_body() -> None:
    respx.post(URL).mock(
        return_value=httpx.Response(
            200, content=b"not json", headers={"content-type": "text/plain"}
        )
    )
    transport = JsonRpcTransport(URL, backoff_factor=0)

    with pytest.raises(AlchemyHttpError):
        transport.call("eth_sendUserOperation")

    transport.close()


def test_context_manager_closes_owned_client() -> None:
    with JsonRpcTransport(URL, backoff_factor=0) as transport:
        assert transport._client.is_closed is False
    assert transport._client.is_closed is True


def test_does_not_close_externally_provided_client() -> None:
    client = httpx.Client()
    transport = JsonRpcTransport(URL, client=client)

    transport.close()

    assert client.is_closed is False
    client.close()


def test_rejects_negative_max_retries() -> None:
    with pytest.raises(ValueError):
        JsonRpcTransport(URL, max_retries=-1)
