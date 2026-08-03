from alchemy_wallet_client import __version__


def test_version_is_a_nonempty_string() -> None:
    assert isinstance(__version__, str)
    assert __version__
