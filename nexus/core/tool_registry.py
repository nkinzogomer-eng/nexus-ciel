from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Any, Callable


class ToolAuthorizationError(PermissionError):
    """A mission did not grant the exact permissions required by a tool."""


class ToolExecutionError(RuntimeError):
    """A registered tool failed during its bounded execution."""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    handler: Callable[[dict[str, Any]], Any]
    required_permissions: frozenset[str] = frozenset()
    risk: str = "read_only"
    idempotent: bool = True


class ToolRegistry:
    """Allowlisted, read-only tool execution with mission-scoped grants.

    Side-effecting tools are intentionally rejected until approval and durable
    idempotency keys are implemented by the host integration.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, tool: ToolSpec) -> None:
        if not tool.name or tool.name in self._tools:
            raise ValueError("tool names must be unique non-empty strings")
        if tool.risk != "read_only" or not tool.idempotent:
            raise ValueError("only read_only, idempotent tools can be registered")
        self._tools[tool.name] = tool

    def list(self) -> list[dict[str, Any]]:
        return [
            {"name": tool.name, "required_permissions": sorted(tool.required_permissions),
             "risk": tool.risk, "idempotent": tool.idempotent}
            for tool in self._tools.values()
        ]

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        allowed_tools: set[str],
        granted_permissions: set[str],
        timeout_s: float,
    ) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolAuthorizationError(f"tool {name!r} is not registered")
        if name not in allowed_tools:
            raise ToolAuthorizationError(f"mission did not authorize tool {name!r}")
        missing = tool.required_permissions - granted_permissions
        if missing:
            raise ToolAuthorizationError(f"mission lacks permissions for {name!r}: {sorted(missing)}")
        if tool.risk != "read_only" or not tool.idempotent:
            raise ToolAuthorizationError(f"tool {name!r} exceeds the safe execution boundary")
        try:
            if inspect.iscoroutinefunction(tool.handler):
                return await asyncio.wait_for(tool.handler(arguments), timeout=timeout_s)
            value = await asyncio.wait_for(asyncio.to_thread(tool.handler, arguments), timeout=timeout_s)
            if inspect.isawaitable(value):
                return await asyncio.wait_for(value, timeout=timeout_s)
            return value
        except asyncio.TimeoutError as exc:
            raise ToolExecutionError(f"tool {name!r} timed out") from exc
        except ToolAuthorizationError:
            raise
        except Exception as exc:
            raise ToolExecutionError(f"tool {name!r} failed: {type(exc).__name__}: {exc}") from exc
