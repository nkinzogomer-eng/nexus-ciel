from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from uuid import uuid4

import pytest

from nexus.actions import ActionExecutor, ActionRecord, ActionRejected, ActionRequest, ApprovalRequired, ToolRegistry, ToolSpec
from nexus.core.mission_journal import MissionJournal
from nexus.persistence import FileSnapshotStore


def make_request(**updates):
    values = {"mission_id": uuid4(), "plan_id": uuid4(), "step_id": uuid4(), "tool_name": "counted", "parameters": {"value": 1}, "idempotency_key": f"key-{uuid4()}", "budget_usd": 1.0}
    values.update(updates)
    return ActionRequest(**values)


def counted_registry(calls, lock=None):
    registry = ToolRegistry()
    def handler(params):
        if lock:
            with lock:
                calls.append(dict(params))
        else:
            calls.append(dict(params))
        return {"ok": True, "value": params["value"]}
    registry.register(ToolSpec(name="counted", description="counted handler", permissions=["demo"], input_schema={"required": ["value"], "properties": {"value": {"type": "number"}}}, idempotency_rule="same identity executes once"), handler)
    return registry


def test_restored_running_action_is_marked_uncertain_and_never_replayed():
    calls = []
    registry = counted_registry(calls)
    request = make_request()
    record = ActionRecord(request=request, status="running")
    journal = MissionJournal()
    executor = ActionExecutor.from_snapshot([record.model_dump(mode="json")], registry, journal=journal)
    result = executor.execute(request, granted_permissions={"demo"})
    assert result.status == "interrupted_uncertain"
    assert result.idempotent_replay is True
    assert calls == []
    assert executor.get(request.action_id).error
    assert any(entry.type == "action_recovery_blocked" for entry in journal.entries())
    assert journal.verify_chain()


@pytest.mark.parametrize("change", [{"budget_usd": 0.5}, {"preconditions": {"state": "different"}}, {"contract_version": 2}])
def test_same_key_with_different_identity_context_is_rejected(change):
    calls = []
    executor = ActionExecutor(counted_registry(calls))
    request = make_request(idempotency_key="collision")
    assert executor.execute(request, granted_permissions={"demo"}).status == "succeeded"
    with pytest.raises(ActionRejected, match="idempotency key"):
        executor.execute(request.model_copy(update=change), granted_permissions={"demo"})
    assert len(calls) == 1


def test_same_key_with_different_permissions_is_rejected():
    calls = []
    executor = ActionExecutor(counted_registry(calls))
    request = make_request(idempotency_key="permissions-collision")
    executor.execute(request, granted_permissions={"demo"})
    with pytest.raises(ActionRejected, match="idempotency key"):
        executor.execute(request, granted_permissions={"demo", "extra"})
    assert len(calls) == 1


def test_unexpected_handler_exception_becomes_uncertain_and_is_not_replayed():
    calls = []
    registry = ToolRegistry()
    def explode(params):
        calls.append(1)
        raise KeyError("unexpected")
    registry.register(ToolSpec(name="explode", description="unexpected", permissions=["demo"], idempotency_rule="unknown"), explode)
    request = make_request(tool_name="explode", parameters={})
    executor = ActionExecutor(registry)
    result = executor.execute(request, granted_permissions={"demo"})
    assert result.status == "interrupted_uncertain"
    assert len(calls) == 1
    replay = executor.execute(request, granted_permissions={"demo"})
    assert replay.status == "interrupted_uncertain" and replay.idempotent_replay is True
    assert len(calls) == 1


def test_two_threads_same_executor_and_key_call_handler_once():
    calls = []
    executor = ActionExecutor(counted_registry(calls, Lock()))
    request = make_request(idempotency_key="concurrent")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: executor.execute(request, granted_permissions={"demo"}), range(2)))
    assert len(calls) == 1
    assert sorted(result.idempotent_replay for result in results) == [False, True]
    assert all(result.status == "succeeded" for result in results)


def test_two_executor_instances_same_registry_and_key_call_handler_once():
    calls = []
    registry = counted_registry(calls, Lock())
    first_executor = ActionExecutor(registry)
    second_executor = ActionExecutor(registry)
    request = make_request(idempotency_key="concurrent-executors")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda executor: executor.execute(request, granted_permissions={"demo"}),
            (first_executor, second_executor),
        ))

    assert len(calls) == 1
    assert sorted(result.idempotent_replay for result in results) == [False, True]
    assert all(result.status == "succeeded" for result in results)


def test_second_executor_persists_coordinated_result_and_restores_without_replay(tmp_path):
    calls = []
    registry = counted_registry(calls, Lock())
    store = FileSnapshotStore(tmp_path / "second-executor.json")
    journal = MissionJournal()
    holder = {}

    def persist_second():
        store.save({"actions": holder["executor"].snapshot()})

    first_executor = ActionExecutor(registry)
    second_executor = ActionExecutor(registry, journal=journal, on_change=persist_second)
    holder["executor"] = second_executor
    request = make_request(idempotency_key="persist-coordinated-result")

    first = first_executor.execute(request, granted_permissions={"demo"})
    second = second_executor.execute(request, granted_permissions={"demo"})

    persisted = store.load()["actions"][0]
    assert first.status == "succeeded"
    assert second.status == "succeeded" and second.idempotent_replay is True
    assert persisted["status"] == "succeeded"
    assert persisted["observation"]["value"] == 1
    assert any(entry.type == "action_coordination_replayed" for entry in journal.entries())

    restored = ActionExecutor.from_snapshot(store.load()["actions"], registry)
    replay = restored.execute(request, granted_permissions={"demo"})
    assert replay.status == "succeeded" and replay.idempotent_replay is True
    assert len(calls) == 1


def test_approval_required_is_authorized_but_never_started():
    calls = []
    registry = ToolRegistry()
    registry.register(ToolSpec(name="approve", description="approval boundary", permissions=["demo"], requires_approval=True, idempotency_rule="once"), lambda params: calls.append(1) or {"ok": True})
    request = make_request(tool_name="approve", parameters={}, idempotency_key="approval-boundary")
    executor = ActionExecutor(registry)
    with pytest.raises(ApprovalRequired):
        executor.execute(request, granted_permissions={"demo"})
    record = executor.get(request.action_id)
    assert record is not None and record.status == "authorized"
    assert record.started_at is None and calls == []


def test_output_limit_after_handler_is_uncertain(monkeypatch):
    calls = []
    registry = ToolRegistry()
    registry.register(ToolSpec(name="large", description="large result", permissions=["demo"], idempotency_rule="once"), lambda params: calls.append(1) or {"payload": "x" * 100})
    monkeypatch.setattr(ActionExecutor, "MAX_OUTPUT_BYTES", 16)
    result = ActionExecutor(registry).execute(make_request(tool_name="large", parameters={}, idempotency_key="large-result"), granted_permissions={"demo"})
    assert result.status == "interrupted_uncertain"
    assert calls == [1]
