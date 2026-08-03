import pytest

from alchemy_wallet_client.smart_account import (
    Eip7702Authorization,
    InvalidAuthorizationError,
    InvalidUserOperationError,
    build_eip7702_user_operation,
    is_address,
    is_hex,
    merge_sponsorship_result,
)

VALID_ADDRESS = "0x1111111111111111111111111111111111111111"
VALID_AUTH = Eip7702Authorization(
    chain_id=8453,
    address=VALID_ADDRESS,
    nonce=0,
    y_parity=1,
    r="0x" + "ab" * 32,
    s="0x" + "cd" * 32,
)


def test_is_address_accepts_valid_address() -> None:
    assert is_address(VALID_ADDRESS) is True


@pytest.mark.parametrize(
    "value",
    [
        "not-an-address",
        "0x123",
        "1111111111111111111111111111111111111111",
        "0x11111111111111111111111111111111111111zz",
    ],
)
def test_is_address_rejects_invalid_values(value: str) -> None:
    assert is_address(value) is False


def test_is_hex_accepts_valid_hex() -> None:
    assert is_hex("0xdeadbeef") is True
    assert is_hex("0x") is True


@pytest.mark.parametrize("value", ["deadbeef", "0xzz", "123"])
def test_is_hex_rejects_invalid_values(value: str) -> None:
    assert is_hex(value) is False


def test_authorization_to_dict_serializes_correctly() -> None:
    auth = Eip7702Authorization(
        chain_id=8453, address=VALID_ADDRESS, nonce=5, y_parity=0, r="0xaa", s="0xbb"
    )

    result = auth.to_dict()

    assert result == {
        "chainId": hex(8453),
        "address": VALID_ADDRESS,
        "nonce": hex(5),
        "yParity": hex(0),
        "r": "0xaa",
        "s": "0xbb",
    }


def test_authorization_rejects_invalid_address() -> None:
    with pytest.raises(InvalidAuthorizationError):
        Eip7702Authorization(
            chain_id=1, address="not-an-address", nonce=0, y_parity=0, r="0xaa", s="0xbb"
        )


def test_authorization_rejects_negative_chain_id() -> None:
    with pytest.raises(InvalidAuthorizationError):
        Eip7702Authorization(
            chain_id=-1, address=VALID_ADDRESS, nonce=0, y_parity=0, r="0xaa", s="0xbb"
        )


def test_authorization_rejects_negative_nonce() -> None:
    with pytest.raises(InvalidAuthorizationError):
        Eip7702Authorization(
            chain_id=1, address=VALID_ADDRESS, nonce=-1, y_parity=0, r="0xaa", s="0xbb"
        )


@pytest.mark.parametrize("y_parity", [-1, 2, 99])
def test_authorization_rejects_invalid_y_parity(y_parity: int) -> None:
    with pytest.raises(InvalidAuthorizationError):
        Eip7702Authorization(
            chain_id=1, address=VALID_ADDRESS, nonce=0, y_parity=y_parity, r="0xaa", s="0xbb"
        )


def test_authorization_rejects_non_hex_r_or_s() -> None:
    with pytest.raises(InvalidAuthorizationError):
        Eip7702Authorization(
            chain_id=1, address=VALID_ADDRESS, nonce=0, y_parity=0, r="not-hex", s="0xbb"
        )


def test_build_eip7702_user_operation_includes_authorization_list() -> None:
    user_op = build_eip7702_user_operation(
        sender=VALID_ADDRESS,
        nonce="0x0",
        call_data="0xdeadbeef",
        authorization=VALID_AUTH,
    )

    assert user_op["sender"] == VALID_ADDRESS
    assert user_op["callData"] == "0xdeadbeef"
    assert user_op["signature"] == "0x"
    assert user_op["authorizationList"] == [VALID_AUTH.to_dict()]
    assert "callGasLimit" not in user_op


def test_build_eip7702_user_operation_includes_optional_gas_fields_when_given() -> None:
    user_op = build_eip7702_user_operation(
        sender=VALID_ADDRESS,
        nonce="0x0",
        call_data="0xdeadbeef",
        authorization=VALID_AUTH,
        call_gas_limit="0x1",
        verification_gas_limit="0x2",
        pre_verification_gas="0x3",
        max_fee_per_gas="0x4",
        max_priority_fee_per_gas="0x5",
    )

    assert user_op["callGasLimit"] == "0x1"
    assert user_op["verificationGasLimit"] == "0x2"
    assert user_op["preVerificationGas"] == "0x3"
    assert user_op["maxFeePerGas"] == "0x4"
    assert user_op["maxPriorityFeePerGas"] == "0x5"


def test_build_eip7702_user_operation_rejects_invalid_sender() -> None:
    with pytest.raises(InvalidUserOperationError):
        build_eip7702_user_operation(
            sender="not-an-address",
            nonce="0x0",
            call_data="0xdeadbeef",
            authorization=VALID_AUTH,
        )


def test_build_eip7702_user_operation_rejects_invalid_call_data() -> None:
    with pytest.raises(InvalidUserOperationError):
        build_eip7702_user_operation(
            sender=VALID_ADDRESS,
            nonce="0x0",
            call_data="not-hex",
            authorization=VALID_AUTH,
        )


def test_merge_sponsorship_result_merges_without_mutating_inputs() -> None:
    user_op = {"sender": VALID_ADDRESS, "callData": "0xdeadbeef"}
    sponsorship_result = {"paymasterAndData": "0xpaymaster", "callGasLimit": "0x1"}

    merged = merge_sponsorship_result(user_op, sponsorship_result)

    assert merged == {
        "sender": VALID_ADDRESS,
        "callData": "0xdeadbeef",
        "paymasterAndData": "0xpaymaster",
        "callGasLimit": "0x1",
    }
    assert user_op == {"sender": VALID_ADDRESS, "callData": "0xdeadbeef"}
    assert sponsorship_result == {"paymasterAndData": "0xpaymaster", "callGasLimit": "0x1"}
