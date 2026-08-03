from alchemy_wallet_client.exceptions import (
    AlchemyError,
    AlchemyHttpError,
    AlchemyRpcError,
    AlchemyTimeoutError,
)


def test_alchemy_rpc_error_repr_includes_code_message_and_data() -> None:
    error = AlchemyRpcError("invalid params", code=-32602, data={"field": "sender"})

    result = repr(error)

    assert "code=-32602" in result
    assert "invalid params" in result
    assert "field" in result


def test_alchemy_http_error_carries_status_code() -> None:
    error = AlchemyHttpError("boom", status_code=503)

    assert error.status_code == 503
    assert str(error) == "boom"


def test_exception_hierarchy() -> None:
    assert issubclass(AlchemyHttpError, AlchemyError)
    assert issubclass(AlchemyRpcError, AlchemyError)
    assert issubclass(AlchemyTimeoutError, AlchemyError)
