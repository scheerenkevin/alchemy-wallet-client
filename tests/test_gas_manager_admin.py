import httpx
import pytest
import respx

from alchemy_wallet_client.exceptions import AlchemyHttpError, AlchemyTimeoutError
from alchemy_wallet_client.gas_manager_admin import GasManagerAdminClient

BASE_URL = "https://manage.g.alchemy.com"


@pytest.fixture
def client() -> GasManagerAdminClient:
    return GasManagerAdminClient("test-auth-token", base_url=BASE_URL, backoff_factor=0)


@respx.mock
def test_create_policy(client: GasManagerAdminClient) -> None:
    policy_in = {"policyName": "keeperos-base", "rules": {"maxSpendUsd": "100"}}
    policy_out = {**policy_in, "id": "policy-1"}
    route = respx.post(f"{BASE_URL}/api/gasManager/policy").mock(
        return_value=httpx.Response(200, json=policy_out)
    )

    result = client.create_policy(policy_in)

    assert result == policy_out
    assert route.calls.last.request.headers["Authorization"] == "Bearer test-auth-token"
    client.close()


@respx.mock
def test_get_policy(client: GasManagerAdminClient) -> None:
    respx.get(f"{BASE_URL}/api/gasManager/policy/policy-1").mock(
        return_value=httpx.Response(200, json={"id": "policy-1", "policyName": "keeperos-base"})
    )

    result = client.get_policy("policy-1")

    assert result == {"id": "policy-1", "policyName": "keeperos-base"}
    client.close()


@respx.mock
def test_list_policies_unwraps_data_envelope(client: GasManagerAdminClient) -> None:
    respx.get(f"{BASE_URL}/api/gasManager/policies").mock(
        return_value=httpx.Response(200, json={"data": [{"id": "policy-1"}, {"id": "policy-2"}]})
    )

    result = client.list_policies()

    assert result == [{"id": "policy-1"}, {"id": "policy-2"}]
    client.close()


@respx.mock
def test_list_policies_handles_bare_list(client: GasManagerAdminClient) -> None:
    respx.get(f"{BASE_URL}/api/gasManager/policies").mock(
        return_value=httpx.Response(200, json=[{"id": "policy-1"}])
    )

    result = client.list_policies()

    assert result == [{"id": "policy-1"}]
    client.close()


@respx.mock
def test_update_policy(client: GasManagerAdminClient) -> None:
    route = respx.patch(f"{BASE_URL}/api/gasManager/policy/policy-1").mock(
        return_value=httpx.Response(200, json={"id": "policy-1", "status": "active"})
    )

    result = client.update_policy("policy-1", {"status": "active"})

    assert result == {"id": "policy-1", "status": "active"}
    assert route.called
    client.close()


@respx.mock
def test_delete_policy_returns_none_on_204(client: GasManagerAdminClient) -> None:
    respx.delete(f"{BASE_URL}/api/gasManager/policy/policy-1").mock(
        return_value=httpx.Response(204)
    )

    result = client.delete_policy("policy-1")

    assert result is None
    client.close()


@respx.mock
def test_retries_on_5xx_then_succeeds(client: GasManagerAdminClient) -> None:
    route = respx.get(f"{BASE_URL}/api/gasManager/policy/policy-1")
    route.side_effect = [
        httpx.Response(503),
        httpx.Response(200, json={"id": "policy-1"}),
    ]

    result = client.get_policy("policy-1")

    assert result == {"id": "policy-1"}
    assert route.call_count == 2
    client.close()


@respx.mock
def test_no_retry_on_4xx(client: GasManagerAdminClient) -> None:
    route = respx.get(f"{BASE_URL}/api/gasManager/policy/missing").mock(
        return_value=httpx.Response(404, json={"message": "not found"})
    )

    with pytest.raises(AlchemyHttpError) as exc_info:
        client.get_policy("missing")

    assert exc_info.value.status_code == 404
    assert route.call_count == 1
    client.close()


@respx.mock
def test_raises_timeout_error_after_retries_exhausted() -> None:
    respx.get(f"{BASE_URL}/api/gasManager/policy/policy-1").mock(
        side_effect=httpx.TimeoutException("timed out")
    )
    client = GasManagerAdminClient(
        "test-auth-token", base_url=BASE_URL, backoff_factor=0, max_retries=1
    )

    with pytest.raises(AlchemyTimeoutError):
        client.get_policy("policy-1")

    client.close()


def test_rejects_negative_max_retries() -> None:
    with pytest.raises(ValueError):
        GasManagerAdminClient("token", max_retries=-1)


def test_context_manager_closes_owned_client() -> None:
    with GasManagerAdminClient("token", base_url=BASE_URL) as client:
        assert client._client.is_closed is False
    assert client._client.is_closed is True
