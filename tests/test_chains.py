import pytest

from alchemy_wallet_client.chains import (
    SUPPORTED_CHAINS,
    Chain,
    build_rpc_url,
    get_chain_by_id,
    get_chain_info,
)

EXPECTED_CHAIN_IDS = {
    Chain.BASE: 8453,
    Chain.ETHEREUM: 1,
    Chain.ARBITRUM: 42161,
    Chain.OPTIMISM: 10,
    Chain.POLYGON: 137,
    Chain.BNB_CHAIN: 56,
    Chain.AVALANCHE: 43114,
}

EXPECTED_NETWORK_SLUGS = {
    Chain.BASE: "base-mainnet",
    Chain.ETHEREUM: "eth-mainnet",
    Chain.ARBITRUM: "arb-mainnet",
    Chain.OPTIMISM: "opt-mainnet",
    Chain.POLYGON: "polygon-mainnet",
    Chain.BNB_CHAIN: "bnb-mainnet",
    Chain.AVALANCHE: "avax-mainnet",
}


def test_all_seven_target_chains_are_supported() -> None:
    assert set(SUPPORTED_CHAINS) == set(Chain)
    assert len(SUPPORTED_CHAINS) == 7


def test_base_is_first_in_supported_chains() -> None:
    assert SUPPORTED_CHAINS[0] == Chain.BASE


@pytest.mark.parametrize("chain", list(Chain))
def test_chain_id_is_correct(chain: Chain) -> None:
    assert get_chain_info(chain).chain_id == EXPECTED_CHAIN_IDS[chain]


@pytest.mark.parametrize("chain", list(Chain))
def test_alchemy_network_slug_is_correct(chain: Chain) -> None:
    assert get_chain_info(chain).alchemy_network == EXPECTED_NETWORK_SLUGS[chain]


@pytest.mark.parametrize("chain", list(Chain))
def test_build_rpc_url_uses_correct_network_and_key(chain: Chain) -> None:
    url = build_rpc_url(chain, "my-api-key")

    expected_slug = EXPECTED_NETWORK_SLUGS[chain]
    assert url == f"https://{expected_slug}.g.alchemy.com/v2/my-api-key"


def test_get_chain_by_id_round_trips_for_all_chains() -> None:
    for chain in Chain:
        chain_id = get_chain_info(chain).chain_id
        assert get_chain_by_id(chain_id) == chain


def test_get_chain_by_id_raises_for_unsupported_id() -> None:
    with pytest.raises(KeyError):
        get_chain_by_id(999999999)


def test_all_chain_ids_are_unique() -> None:
    chain_ids = [get_chain_info(chain).chain_id for chain in Chain]
    assert len(chain_ids) == len(set(chain_ids))
