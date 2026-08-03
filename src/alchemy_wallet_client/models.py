"""JSON-RPC 2.0 request/response models shared by the Bundler and Gas
Manager Sponsorship API clients.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

JsonRpcParams = list[Any] | dict[str, Any] | None


@dataclass(frozen=True)
class JsonRpcRequest:
    """A single JSON-RPC 2.0 request object."""

    method: str
    params: JsonRpcParams = None
    id: int | str = 1
    jsonrpc: str = "2.0"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": self.method,
        }
        if self.params is not None:
            payload["params"] = self.params
        return payload


@dataclass(frozen=True)
class JsonRpcError:
    """A JSON-RPC 2.0 error object."""

    code: int
    message: str
    data: Any = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JsonRpcError:
        return cls(code=data["code"], message=data.get("message", ""), data=data.get("data"))


@dataclass(frozen=True)
class JsonRpcResponse:
    """A JSON-RPC 2.0 response object: either `result` or `error` is set."""

    id: int | str | None
    result: Any = None
    error: JsonRpcError | None = None
    jsonrpc: str = "2.0"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JsonRpcResponse:
        error = JsonRpcError.from_dict(data["error"]) if data.get("error") is not None else None
        return cls(
            id=data.get("id"),
            result=data.get("result"),
            error=error,
            jsonrpc=data.get("jsonrpc", "2.0"),
        )
