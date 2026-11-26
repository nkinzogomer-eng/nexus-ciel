from uuid import uuid4

import pytest

from nexus.actions import ActionRequest, ApprovalRequired
from nexus.persistence import FileSnapshotStore, PersistentRuntime


def _write_request():
    return ActionRequest(
        mission_id=uuid4(),
        plan_id=uuid4(),
        step_id=uuid4(),
        tool_name="write_workspace",
        parameters={"path": "approved.txt", "content": "durable approval"},
        idempotency_key="phase5-persistent-approval",
        budget_usd=1.0,
    )


def test_sensitive_action_creates_persisted_pending_approval_and_resumes_after_restart(tmp_path):
    store = FileSnapshotStore(tmp_path / "runtime.json")
    first_runtime = PersistentRuntime(store, workspace_root=tmp_path)
    request = _write_request()

    with pytest.raises(ApprovalRequired):
        first_runtime.action_executor.execute(
            request, granted_permissions={"workspace.write"}
        )
    record = first_runtime.action_executor.get(request.action_id)
    assert record is not None
    assert record.identity_hash
    assert first_runtime.approval_ledger.get(record.identity_hash).status == "pending"

    restarted = PersistentRuntime(store, workspace_root=tmp_path)
    restored = restarted.approval_ledger.get(record.identity_hash)
    assert restored is not None
    assert restored.status == "pending"

    restarted.action_executor.approve(record.identity_hash, approver="operator-1")
    result = restarted.action_executor.execute(
        request, granted_permissions={"workspace.write"}, approval=True
    )
    assert result.status == "succeeded"
    assert (tmp_path / "approved.txt").read_text() == "durable approval"
    assert restarted.approval_ledger.get(record.identity_hash).status == "approved"

    restored_again = PersistentRuntime(store, workspace_root=tmp_path)
    replay = restored_again.action_executor.execute(
        request, granted_permissions={"workspace.write"}, approval=True
    )
    assert replay.idempotent_replay is True
    assert replay.status == "succeeded"


def test_persistent_approval_is_bound_to_exact_action_identity(tmp_path):
    store = FileSnapshotStore(tmp_path / "runtime.json")
    runtime = PersistentRuntime(store, workspace_root=tmp_path)
    request = _write_request()
    with pytest.raises(ApprovalRequired):
        runtime.action_executor.execute(request, granted_permissions={"workspace.write"})
    record = runtime.action_executor.get(request.action_id)
    runtime.action_executor.approve(record.identity_hash, approver="operator-1")

    conflicting = request.model_copy(update={"parameters": {"path": "other.txt", "content": "not approved"}})
    with pytest.raises(Exception, match="idempotency key"):
        runtime.action_executor.execute(
            conflicting, granted_permissions={"workspace.write"}, approval=True
        )
    assert not (tmp_path / "other.txt").exists()
