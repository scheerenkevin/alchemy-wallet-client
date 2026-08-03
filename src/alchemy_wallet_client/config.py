"""Configuration and authentication handling.

The Alchemy API key is always read from an environment variable — never
hardcoded, never accepted as a plain positional argument that might get
logged or committed by accident, and never included in `repr()`/`str()` of
any config or client object.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

#: Name of the environment variable holding the Alchemy API key by default.
DEFAULT_API_KEY_ENV_VAR = "ALCHEMY_API_KEY"


class MissingApiKeyError(RuntimeError):
    """Raised when no Alchemy API key can be found."""


@dataclass(frozen=True)
class AlchemyConfig:
    """Holds the credentials/config needed to talk to Alchemy's APIs.

    The API key is deliberately excluded from the generated `repr()` (via
    `field(repr=False)`) so it can never leak into logs, tracebacks, or
    `print()`/debugger output of a config or client object.
    """

    api_key: str = field(repr=False)

    @classmethod
    def from_env(cls, env_var: str = DEFAULT_API_KEY_ENV_VAR) -> AlchemyConfig:
        """Build a config by reading the API key from an environment variable.

        Raises:
            MissingApiKeyError: if the environment variable is unset or empty.
        """
        api_key = os.environ.get(env_var)
        if not api_key:
            raise MissingApiKeyError(
                f"Alchemy API key not found. Set the {env_var} environment "
                "variable (never hardcode it in source)."
            )
        return cls(api_key=api_key)
