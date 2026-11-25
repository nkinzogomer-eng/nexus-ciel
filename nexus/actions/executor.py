from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any, Iterable
from uuid import UUID

from .models import ActionRecord, ActionRequest, ActionResult
from .registry import ToolRegistry, ToolRegistryError


class ActionEngineError(ValueError):
    pass


class ActionRejected(ActionEngineError):
    pass


class ApprovalRequired(ActionRejected):
    pass


class ActionExecutor:
    """Execute only allowlisted deterministic handlers in a controlled boundary."""

    TERMINAL = {"succeeded", "failed", "partial", "uncertain", "cancelled", "rejected"}

    def __init__(self, registry: ToolRegistry, *, journal: Any | None = None, records: Iterable[ActionRecord] | None = None, on_change=None) -> None:
        self.registry = registry
        self.journal = journal
        self._records = {record.request.action_id: record for record in records or []}
        self._by_key = {record.request.idempotency_key: record.request.action_id for record in self._records.values()}
        self._lock = RLock()
        self._on_change = on_change or (lambda: None)

    def request(self, request: ActionRequest) -> ActionRecord:
        with self._lock:
            existing_id = self._by_key.get(request.idempotency_key)
            if existing_id is not None:
                existing = self._records[existing_id]
                if (
                    existing.request.mission_id != request.mission_id
                    or existing.request.plan_id != request.plan_id
                    or existing.request.step_id != request.step_id
                    or existing.request.tool_name != request.tool_name
                    or existing.request.parameters != request.parameters
                ):
                    raise ActionRejected("idempotency key is bound to a different action request")
                return existing
            record = ActionRecord(request=request)
            self._records[request.action_id] = record
            self._by_key[request.idempotency_key] = request.action_id
            self._event(request, "action_requested", {"tool_name": request.tool_name, "step_id": str(request.step_id)})
            self._changed()
            return record

    def execute(
        self,
        request: ActionRequest,
        *,
        granted_permissions: set[str] | None = None,
        facts: dict[str, Any] | None = None,
        approval: bool = False,
        budget_remaining_usd: float | None = None,
    ) -> ActionResult:
        with self._lock:
            record = self.request(request)
            if record.status in self.TERMINAL:
                return ActionResult(action_id=request.action_id, status=record.status, outcome=record.outcome, observation=dict(record.observation), error=record.error, actual_cost_usd=record.actual_cost_usd, idempotent_replay=True)
            spec = self.registry.get(request.tool_name)
            if spec is None or not spec.available:
                return self._reject(record, f"tool is not registered or unavailable: {request.tool_name}")
            try:
                self._validate_parameters(spec.input_schema, request.parameters)
                permissions = granted_permissions or set()
                missing = set(spec.permissions) - permissions
                if missing:
                    raise ActionRejected(f"missing permissions: {sorted(missing)}")
                if request.budget_usd < spec.estimated_cost_usd:
                    raise ActionRejected("action budget is below tool estimated cost")
                if budget_remaining_usd is not None and spec.estimated_cost_usd > budget_remaining_usd:
                    raise ActionRejected("mission budget is below tool estimated cost")
                supplied_facts = facts or {}
                if any(supplied_facts.get(key) != value for key, value in request.preconditions.items()):
                    raise ActionRejected("action preconditions are not satisfied")
                needs_approval = spec.requires_approval or spec.risk_level == "high"
                record.tool_id = spec.tool_id
                record.permissions = sorted(permissions)
                record.estimated_cost_usd = spec.estimated_cost_usd
                record.approval_required = needs_approval
                if needs_approval and not approval:
                    self._event(request, "action_approval_required", {"tool_name": spec.name, "risk_level": spec.risk_level})
                    self._changed()
                    raise ApprovalRequired(f"approval required for tool {spec.name}")
                record.approved = approval or not needs_approval
                record.status = "authorized"
                self._event(request, "action_authorized", {"tool_name": spec.name, "permissions": record.permissions, "approved": record.approved})
                record.status = "running"
                record.started_at = datetime.now(timezone.utc)
                self._event(request, "action_started", {"tool_name": spec.name})
                observation = self.registry.handler(spec.name)(dict(request.parameters))
                outcome = observation.pop("_outcome", "success")
                if outcome not in {"success", "failure", "partial", "uncertain"}:
                    raise ActionEngineError(f"invalid tool outcome: {outcome}")
                record.outcome = outcome
                record.status = outcome if outcome != "success" else "succeeded"
                record.observation = observation
                record.actual_cost_usd = spec.estimated_cost_usd
                record.finished_at = datetime.now(timezone.utc)
                self._event(request, "action_observed", {"tool_name": spec.name, "status": record.status, "outcome": outcome, "observation": observation, "actual_cost_usd": record.actual_cost_usd})
                self._changed()
                return ActionResult(action_id=request.action_id, status=record.status, outcome=outcome, observation=observation, actual_cost_usd=record.actual_cost_usd)
            except ApprovalRequired:
                raise
            except (ActionRejected, ToolRegistryError, ValueError, RuntimeError) as exc:
                record.status = "rejected" if isinstance(exc, ActionRejected) or isinstance(exc, ToolRegistryError) else "failed"
                record.outcome = "failure"
                record.error = str(exc)
                record.finished_at = datetime.now(timezone.utc)
                self._event(request, "action_rejected" if record.status == "rejected" else "action_failed", {"tool_name": request.tool_name, "error": str(exc)})
                self._changed()
                return ActionResult(action_id=request.action_id, status=record.status, outcome="failure", error=str(exc))

    def get(self, action_id: UUID) -> ActionRecord | None:
        return self._records.get(action_id)

    def list(self) -> list[ActionRecord]:
        return list(self._records.values())

    def snapshot(self) -> list[dict[str, Any]]:
        return [record.model_dump(mode="json") for record in self._records.values()]

    @classmethod
    def from_snapshot(cls, records: list[dict[str, Any]], registry: ToolRegistry, *, journal: Any | None = None, on_change=None) -> "ActionExecutor":
        return cls(registry, journal=journal, records=[ActionRecord.model_validate(item) for item in records], on_change=on_change)

    def _reject(self, record: ActionRecord, reason: str) -> ActionResult:
        record.status = "rejected"
        record.outcome = "failure"
        record.error = reason
        record.finished_at = datetime.now(timezone.utc)
        self._event(record.request, "action_rejected", {"tool_name": record.request.tool_name, "error": reason})
        self._changed()
        return ActionResult(action_id=record.request.action_id, status="rejected", outcome="failure", error=reason)

    @staticmethod
    def _validate_parameters(schema: dict[str, Any], parameters: dict[str, Any]) -> None:
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        missing = [key for key in required if key not in parameters]
        if missing:
            raise ActionRejected(f"missing required parameters: {missing}")
        unexpected = sorted(set(parameters) - set(properties))
        if properties and unexpected:
            raise ActionRejected(f"unexpected parameters: {unexpected}")
        for key, value in parameters.items():
            expected = properties.get(key, {}).get("type")
            if expected == "string" and not isinstance(value, str):
                raise ActionRejected(f"parameter {key} must be a string")
            if expected == "number" and (not isinstance(value, (int, float)) or isinstance(value, bool)):
                raise ActionRejected(f"parameter {key} must be a number")
            if expected == "array" and not isinstance(value, list):
                raise ActionRejected(f"parameter {key} must be an array")

    def _event(self, request: ActionRequest, event_type: str, payload: dict[str, Any]) -> None:
        if self.journal is not None:
            self.journal.append(request.mission_id, event_type, "action_executor", {"action_id": str(request.action_id), **payload})

    def _changed(self) -> None:
        self._on_change()
