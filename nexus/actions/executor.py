from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from collections import OrderedDict
from threading import RLock
from weakref import WeakKeyDictionary
from typing import Any, Iterable
from uuid import UUID

from .approval import ApprovalLedger
from .models import ActionRecord, ActionRequest, ActionResult
from .registry import ToolRegistry, ToolRegistryError


class ActionEngineError(ValueError):
    pass


class ActionRejected(ActionEngineError):
    pass


class ApprovalRequired(ActionRejected):
    pass


class ActionEffectUncertain(Exception):
    """The handler ran, but its effect/result cannot be safely classified."""


class ActionExecutor:
    """Execute allowlisted handlers with durable, conservative recovery semantics."""

    CONTRACT_VERSION = 1
    MAX_INPUT_BYTES = 256_000
    MAX_OUTPUT_BYTES = 1_000_000
    TERMINAL = {
        "succeeded", "failed", "partial", "uncertain", "interrupted_uncertain",
        "cancelled", "rejected",
    }
    COORDINATION_CACHE_LIMIT = 1024
    _coordination_guard = RLock()
    _coordination_entries: WeakKeyDictionary[Any, OrderedDict[str, dict[str, Any]]] = WeakKeyDictionary()

    def __init__(self, registry: ToolRegistry, *, journal: Any | None = None,
                 records: Iterable[ActionRecord] | None = None, on_change=None,
                 approval_ledger: ApprovalLedger | None = None) -> None:
        self.registry = registry
        self.journal = journal
        self._records = {record.request.action_id: record for record in records or []}
        self._by_key = {record.request.idempotency_key: record.request.action_id for record in self._records.values()}
        self._lock = RLock()
        self._on_change = on_change or (lambda: None)
        self.approval_ledger = approval_ledger
        self._recover_running_records()

    def request(self, request: ActionRequest, *, identity_hash: str | None = None,
                identity_context: dict[str, Any] | None = None) -> ActionRecord:
        with self._lock:
            existing_id = self._by_key.get(request.idempotency_key)
            if existing_id is not None:
                existing = self._records[existing_id]
                if identity_hash is None:
                    identity_hash, identity_context = self._identity_for_request(
                        request, permissions=existing.permissions, budget_remaining_usd=None,
                        tool_id=existing.tool_id,
                    )
                if existing.identity_hash is None:
                    existing.identity_hash = identity_hash
                    existing.identity_context = identity_context or {}
                    self._changed()
                elif existing.identity_hash != identity_hash:
                    raise ActionRejected("idempotency key is bound to a different action identity")
                return existing
            record = ActionRecord(request=request, identity_hash=identity_hash,
                                 identity_context=identity_context or {})
            self._records[request.action_id] = record
            self._by_key[request.idempotency_key] = request.action_id
            self._event(request, "action_requested", {
                "tool_name": request.tool_name, "step_id": str(request.step_id),
                "identity_hash": identity_hash,
            })
            self._changed()
            return record

    def execute(self, request: ActionRequest, *, granted_permissions: set[str] | None = None,
                facts: dict[str, Any] | None = None, approval: bool = False,
                budget_remaining_usd: float | None = None) -> ActionResult:
        with self._lock:
            permissions = set(granted_permissions or set())
            spec = self.registry.get(request.tool_name)
            identity_hash, identity_context = self._identity_for_request(
                request, permissions=permissions, budget_remaining_usd=budget_remaining_usd,
                tool_id=spec.tool_id if spec is not None else None,
            )
            record = self.request(request, identity_hash=identity_hash,
                                  identity_context=identity_context)
            if record.status in self.TERMINAL:
                return self._result(record, replay=True)
            if record.status == "running":
                self._mark_interrupted(record, "action is already running; automatic replay is forbidden")
                return self._result(record, replay=True)
            if spec is None or not spec.available:
                return self._reject(record, f"tool is not registered or unavailable: {request.tool_name}")
            try:
                self._validate_parameters(spec.input_schema, request.parameters)
                self._assert_input_size(request.parameters)
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
                record.status = "authorized"
                self._event(request, "action_authorized", {
                    "tool_name": spec.name, "permissions": record.permissions,
                    "approved": approval or not needs_approval,
                    "identity_hash": record.identity_hash,
                })
                self._changed()
                if needs_approval and not approval:
                    if self.approval_ledger is not None:
                        self.approval_ledger.ensure_pending(
                            identity_hash=record.identity_hash or "",
                            action_id=request.action_id,
                            tool_name=spec.name,
                            context=record.identity_context,
                        )
                        self._event(request, "action_approval_pending", {
                            "tool_name": spec.name, "identity_hash": record.identity_hash,
                        })
                        self._changed()
                    self._event(request, "action_approval_required", {
                        "tool_name": spec.name, "risk_level": spec.risk_level,
                    })
                    self._changed()
                    raise ApprovalRequired(f"approval required for tool {spec.name}")
                if needs_approval and self.approval_ledger is not None and not self.approval_ledger.is_approved(record.identity_hash or ""):
                    raise ApprovalRequired("approval is not persistently granted for this exact action")
                record.approved = approval or not needs_approval
                record.status = "running"
                record.started_at = datetime.now(timezone.utc)
                self._event(request, "action_started", {"tool_name": spec.name})
                self._changed()
                return self._execute_started(record, spec, request)
            except ApprovalRequired:
                raise
            except (ActionRejected, ToolRegistryError, ValueError, RuntimeError) as exc:
                return self._finish_failure(record, str(exc), rejected=isinstance(exc, (ActionRejected, ToolRegistryError)))
            except BaseException as exc:
                if record.status not in self.TERMINAL:
                    self._mark_interrupted(record, f"unexpected exception before completion: {type(exc).__name__}: {exc}")
                raise

    def _execute_started(self, record: ActionRecord, spec: Any, request: ActionRequest) -> ActionResult:
        """Run one started handler under a process-local per-key coordinator."""
        coordination_key = request.idempotency_key
        with self._coordination_guard:
            entries = self._coordination_entries.setdefault(self.registry, OrderedDict())
            entry = entries.setdefault(coordination_key, {"lock": RLock(), "result": None, "identity": None})
            entries.move_to_end(coordination_key)
            lock = entry["lock"]
        with lock:
            cached = entry["result"]
            if cached is not None:
                if entry["identity"] != record.identity_hash:
                    raise ActionRejected("idempotency key is bound to a different action identity")
                self._copy_result_to_record(record, cached)
                self._event(request, "action_coordination_replayed", {
                    "status": cached.status, "source": "process_local_registry_coordinator",
                })
                self._changed()
                return self._result(record, replay=True)
            started = record.started_at
            try:
                observation = self.registry.handler(spec.name)(dict(request.parameters))
                if not isinstance(observation, dict):
                    raise TypeError("tool handler must return an object")
                self._assert_output_size(observation)
                outcome = observation.pop("_outcome", "success")
                if outcome not in {"success", "failure", "partial", "uncertain"}:
                    raise ActionEngineError(f"invalid tool outcome: {outcome}")
                record.outcome = outcome
                record.status = outcome if outcome != "success" else "succeeded"
                record.observation = observation
                record.actual_cost_usd = spec.estimated_cost_usd
                record.finished_at = datetime.now(timezone.utc)
                elapsed = (record.finished_at - started).total_seconds()
                if elapsed > spec.timeout_s:
                    self._mark_interrupted(record, f"handler exceeded timeout of {spec.timeout_s}s")
                else:
                    self._event(request, "action_observed", {
                        "tool_name": spec.name, "status": record.status,
                        "outcome": outcome, "observation": observation,
                        "actual_cost_usd": record.actual_cost_usd,
                    })
                    self._changed()
                result = self._result(record)
                entry["result"] = result
                entry["identity"] = record.identity_hash or ""
                self._trim_coordination_cache(entries)
                return result
            except ActionEffectUncertain as exc:
                self._mark_interrupted(record, str(exc))
                result = self._result(record)
                entry["result"] = result
                entry["identity"] = record.identity_hash or ""
                self._trim_coordination_cache(entries)
                return result
            except (ActionRejected, ToolRegistryError, ValueError, RuntimeError) as exc:
                result = self._finish_failure(record, str(exc), rejected=isinstance(exc, (ActionRejected, ToolRegistryError)))
                entry["result"] = result
                entry["identity"] = record.identity_hash or ""
                self._trim_coordination_cache(entries)
                return result
            except Exception as exc:
                self._mark_interrupted(record, f"unexpected exception after handler start: {type(exc).__name__}: {exc}")
                result = self._result(record)
                entry["result"] = result
                entry["identity"] = record.identity_hash or ""
                self._trim_coordination_cache(entries)
                return result
            except BaseException as exc:
                self._mark_interrupted(record, f"unexpected interruption after handler start: {type(exc).__name__}: {exc}")
                raise

    @classmethod
    def _trim_coordination_cache(cls, entries: OrderedDict[str, dict[str, Any]]) -> None:
        while len(entries) > cls.COORDINATION_CACHE_LIMIT:
            key, entry = next(iter(entries.items()))
            if entry["lock"].acquire(blocking=False):
                try:
                    if entry["result"] is not None:
                        entries.pop(key, None)
                    else:
                        entries.move_to_end(key)
                finally:
                    entry["lock"].release()
            else:
                entries.move_to_end(key)
                break

    @staticmethod
    def _copy_result_to_record(record: ActionRecord, result: ActionResult) -> None:
        record.status = result.status
        record.outcome = result.outcome
        record.observation = dict(result.observation)
        record.error = result.error
        record.actual_cost_usd = result.actual_cost_usd
        record.finished_at = datetime.now(timezone.utc)

    def approve(self, identity_hash: str, *, approver: str, reason: str = "") -> Any:
        if self.approval_ledger is None:
            raise ActionEngineError("persistent approval ledger is not configured")
        with self._lock:
            item = self.approval_ledger.approve(identity_hash, approver=approver, reason=reason)
            self._event_by_identity(identity_hash, "action_approval_granted", {
                "approver": approver, "approval_id": str(item.approval_id),
            })
            self._changed()
            return item

    def reject_approval(self, identity_hash: str, *, approver: str, reason: str) -> Any:
        if self.approval_ledger is None:
            raise ActionEngineError("persistent approval ledger is not configured")
        with self._lock:
            item = self.approval_ledger.reject(identity_hash, approver=approver, reason=reason)
            self._event_by_identity(identity_hash, "action_approval_rejected", {
                "approver": approver, "approval_id": str(item.approval_id),
            })
            self._changed()
            return item

    def get(self, action_id: UUID) -> ActionRecord | None:
        return self._records.get(action_id)

    def list(self) -> list[ActionRecord]:
        return list(self._records.values())

    def snapshot(self) -> list[dict[str, Any]]:
        return [record.model_dump(mode="json") for record in self._records.values()]

    @classmethod
    def from_snapshot(cls, records: list[dict[str, Any]], registry: ToolRegistry, *,
                      journal: Any | None = None, on_change=None,
                      approval_ledger: ApprovalLedger | None = None) -> "ActionExecutor":
        return cls(registry, journal=journal,
                   records=[ActionRecord.model_validate(item) for item in records],
                   on_change=on_change, approval_ledger=approval_ledger)

    def _recover_running_records(self) -> None:
        for record in self._records.values():
            if record.status == "running":
                self._mark_interrupted(record, "restored from running state; automatic replay disabled")

    def _mark_interrupted(self, record: ActionRecord, reason: str) -> None:
        record.status = "interrupted_uncertain"
        record.outcome = "uncertain"
        record.error = reason
        record.finished_at = datetime.now(timezone.utc)
        self._event(record.request, "action_recovery_blocked", {
            "previous_status": "running", "new_status": record.status, "reason": reason,
        })
        self._changed()

    def _finish_failure(self, record: ActionRecord, reason: str, *, rejected: bool) -> ActionResult:
        record.status = "rejected" if rejected else "failed"
        record.outcome = "failure"
        record.error = reason
        record.finished_at = datetime.now(timezone.utc)
        self._event(record.request, "action_rejected" if rejected else "action_failed", {
            "tool_name": record.request.tool_name, "error": reason,
        })
        self._changed()
        return self._result(record)

    def _reject(self, record: ActionRecord, reason: str) -> ActionResult:
        return self._finish_failure(record, reason, rejected=True)

    def _result(self, record: ActionRecord, *, replay: bool = False) -> ActionResult:
        return ActionResult(
            action_id=record.request.action_id, status=record.status, outcome=record.outcome,
            observation=dict(record.observation), error=record.error,
            actual_cost_usd=record.actual_cost_usd, idempotent_replay=replay,
        )

    def _identity_for_request(self, request: ActionRequest, *, permissions: set[str],
                              budget_remaining_usd: float | None, tool_id: UUID | None) -> tuple[str, dict[str, Any]]:
        context = {
            "contract_version": request.contract_version,
            "executor_contract_version": self.CONTRACT_VERSION,
            "mission_id": str(request.mission_id), "plan_id": str(request.plan_id),
            "step_id": str(request.step_id), "tool_name": request.tool_name,
            # ToolSpec.tool_id is generated per registry instance; the stable
            # tool identity is the contract version plus tool_name.
            "tool_id": None,
            "parameters": request.parameters, "preconditions": request.preconditions,
            "permissions": sorted(permissions), "budget_usd": request.budget_usd,
            "budget_remaining_usd": budget_remaining_usd,
            "limits": {"max_input_bytes": self.MAX_INPUT_BYTES, "max_output_bytes": self.MAX_OUTPUT_BYTES},
        }
        encoded = json.dumps(context, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest(), context

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

    def _assert_input_size(self, parameters: dict[str, Any]) -> None:
        size = len(json.dumps(parameters, sort_keys=True, default=str).encode("utf-8"))
        if size > self.MAX_INPUT_BYTES:
            raise ActionRejected(f"action input exceeds {self.MAX_INPUT_BYTES} bytes")

    def _assert_output_size(self, observation: dict[str, Any]) -> None:
        size = len(json.dumps(observation, sort_keys=True, default=str).encode("utf-8"))
        if size > self.MAX_OUTPUT_BYTES:
            raise ActionEffectUncertain(f"action output exceeds {self.MAX_OUTPUT_BYTES} bytes")

    def _event(self, request: ActionRequest, event_type: str, payload: dict[str, Any]) -> None:
        if self.journal is not None:
            self.journal.append(request.mission_id, event_type, "action_executor", {"action_id": str(request.action_id), **payload})

    def _event_by_identity(self, identity_hash: str, event_type: str, payload: dict[str, Any]) -> None:
        for record in self._records.values():
            if record.identity_hash == identity_hash:
                self._event(record.request, event_type, payload)
                return

    def _changed(self) -> None:
        self._on_change()
