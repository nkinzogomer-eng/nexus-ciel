from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .models import ToolSpec


class ToolRegistryError(ValueError):
    pass


Handler = Callable[[dict[str, Any]], dict[str, Any]]


class ToolRegistry:
    """Allowlist of deterministic tools; it never resolves arbitrary callables."""

    def __init__(self, *, workspace_root: str | Path | None = None) -> None:
        self.workspace_root = Path(workspace_root).resolve() if workspace_root is not None else None
        self._specs: dict[str, ToolSpec] = {}
        self._handlers: dict[str, Handler] = {}

    def register(self, spec: ToolSpec, handler: Handler) -> ToolSpec:
        if spec.name in self._specs:
            raise ToolRegistryError(f"tool already registered: {spec.name}")
        self._specs[spec.name] = spec
        self._handlers[spec.name] = handler
        return spec

    def get(self, name: str) -> ToolSpec | None:
        return self._specs.get(name)

    def handler(self, name: str) -> Handler:
        try:
            return self._handlers[name]
        except KeyError as exc:
            raise ToolRegistryError(f"tool is not registered: {name}") from exc

    def list(self) -> list[ToolSpec]:
        return list(self._specs.values())

    @classmethod
    def deterministic(cls, *, workspace_root: str | Path | None = None) -> "ToolRegistry":
        registry = cls(workspace_root=workspace_root)

        def calculate(params: dict[str, Any]) -> dict[str, Any]:
            operation = params.get("operation")
            values = params.get("values")
            if operation not in {"add", "multiply"} or not isinstance(values, list) or not values or not all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in values):
                raise ValueError("calculate expects operation add|multiply and a non-empty numeric values list")
            result = sum(values) if operation == "add" else _product(values)
            return {"ok": True, "result": result, "operation": operation, "count": len(values)}

        def read_workspace(params: dict[str, Any]) -> dict[str, Any]:
            path = registry.safe_path(params.get("path"))
            if not path.is_file():
                raise ValueError("workspace resource does not exist")
            return {"path": str(path.relative_to(registry.workspace_root)), "content": path.read_text(encoding="utf-8")}

        def write_workspace(params: dict[str, Any]) -> dict[str, Any]:
            path = registry.safe_path(params.get("path"))
            content = params.get("content")
            if not isinstance(content, str) or len(content) > 100_000:
                raise ValueError("content must be a string of at most 100000 characters")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return {"path": str(path.relative_to(registry.workspace_root)), "bytes": len(content.encode("utf-8"))}

        def verify_workspace(params: dict[str, Any]) -> dict[str, Any]:
            path = registry.safe_path(params.get("path"))
            expected = params.get("expected_content")
            if not isinstance(expected, str) or not path.is_file():
                raise ValueError("file verification target is unavailable")
            actual = path.read_text(encoding="utf-8")
            if actual != expected:
                raise ValueError("workspace content does not match expected content")
            return {"verified": True, "path": str(path.relative_to(registry.workspace_root))}

        def simulated_failure(params: dict[str, Any]) -> dict[str, Any]:
            raise RuntimeError(str(params.get("reason", "simulated deterministic failure")))

        def simulated_uncertain(params: dict[str, Any]) -> dict[str, Any]:
            return {"_outcome": "uncertain", "reason": str(params.get("reason", "effect cannot be confirmed"))}

        registry.register(ToolSpec(name="calculate", description="Deterministic arithmetic without external effects.", input_schema={"required": ["operation", "values"], "properties": {"operation": {"type": "string"}, "values": {"type": "array"}}}, permissions=["compute"], estimated_cost_usd=0.01, idempotency_rule="same key returns the recorded result", verification_conditions=[{"key": "result", "operator": "exists", "expected": True}]), calculate)
        registry.register(ToolSpec(name="read_workspace", description="Read one UTF-8 file inside the configured temporary workspace.", input_schema={"required": ["path"], "properties": {"path": {"type": "string"}}}, permissions=["workspace.read"], idempotency_rule="read is safe to repeat", access_scope="workspace"), read_workspace)
        registry.register(ToolSpec(name="write_workspace", description="Write one UTF-8 file inside the configured temporary workspace.", input_schema={"required": ["path", "content"], "properties": {"path": {"type": "string"}, "content": {"type": "string"}}}, permissions=["workspace.write"], risk_level="medium", reversible=True, requires_approval=True, idempotency_rule="same key is executed at most once", access_scope="workspace"), write_workspace)
        registry.register(ToolSpec(name="verify_workspace", description="Verify exact UTF-8 content inside the configured temporary workspace.", input_schema={"required": ["path", "expected_content"], "properties": {"path": {"type": "string"}, "expected_content": {"type": "string"}}}, permissions=["workspace.read"], idempotency_rule="verification is safe to repeat", access_scope="workspace"), verify_workspace)
        registry.register(ToolSpec(name="simulated_failure", description="Deterministic failure for recovery tests.", permissions=["demo.simulate"], idempotency_rule="failure has no external effect"), simulated_failure)
        registry.register(ToolSpec(name="simulated_uncertain", description="Deterministic uncertain outcome for recovery tests.", permissions=["demo.simulate"], idempotency_rule="uncertain result is never replayed automatically"), simulated_uncertain)
        return registry

    def safe_path(self, relative: Any) -> Path:
        if self.workspace_root is None:
            raise ToolRegistryError("workspace tools require an explicit controlled workspace")
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            raise ToolRegistryError("workspace path must be a non-empty relative path")
        candidate = (self.workspace_root / relative).resolve()
        if candidate != self.workspace_root and self.workspace_root not in candidate.parents:
            raise ToolRegistryError("workspace path escapes the controlled workspace")
        return candidate


def _product(values: list[int | float]) -> int | float:
    result: int | float = 1
    for value in values:
        result *= value
    return result
