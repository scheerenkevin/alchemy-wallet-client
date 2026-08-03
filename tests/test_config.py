import pytest

from alchemy_wallet_client.config import (
    DEFAULT_API_KEY_ENV_VAR,
    AlchemyConfig,
    MissingApiKeyError,
)


def test_from_env_reads_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(DEFAULT_API_KEY_ENV_VAR, "secret-key-123")

    config = AlchemyConfig.from_env()

    assert config.api_key == "secret-key-123"


def test_from_env_raises_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(DEFAULT_API_KEY_ENV_VAR, raising=False)

    with pytest.raises(MissingApiKeyError):
        AlchemyConfig.from_env()


def test_from_env_raises_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(DEFAULT_API_KEY_ENV_VAR, "")

    with pytest.raises(MissingApiKeyError):
        AlchemyConfig.from_env()


def test_from_env_supports_custom_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(DEFAULT_API_KEY_ENV_VAR, raising=False)
    monkeypatch.setenv("CUSTOM_ALCHEMY_KEY", "secret-key-456")

    config = AlchemyConfig.from_env(env_var="CUSTOM_ALCHEMY_KEY")

    assert config.api_key == "secret-key-456"


def test_api_key_never_appears_in_repr_or_str(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(DEFAULT_API_KEY_ENV_VAR, "super-secret-value")

    config = AlchemyConfig.from_env()

    assert "super-secret-value" not in repr(config)
    assert "super-secret-value" not in str(config)
