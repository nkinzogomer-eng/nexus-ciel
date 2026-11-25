from uuid import uuid4

import pytest

from nexus.actions import ActionExecutor, ActionRejected, ActionRequest, ApprovalRequired, ToolRegistry
from nexus.cognitive import CognitiveEngine, GoalUnderstanding
from nexus.core.mission_journal import MissionJournal
from nexus.persistence import FileSnapshotStore, PersistentRuntime
from nexus.planning import PlanEngine


def request(tool_name="calculate", **parameters):
    return ActionRequest(
        mission_id=uuid4(),
        plan_id=uuid4(),
        step_id=uuid4(),
        tool_name=tool_name,
        parameters=parameters,
        idempotency_key=f"key-{uuid4()}",
        budget_usd=1.0,
    )


def test_calculate_is_real_deterministic_action_and_idempotent():
    journal = MissionJournal()
    executor = ActionExecutor(ToolRegistry.deterministic(), journal=journal)
    action = request(operation="add", values=[2, 3])
    first = executor.execute(action, granted_permissions={"compute"})
    second = executor.execute(action, granted_permissions={"compute"})
    assert first.status == "succeeded"
    assert first.observation["result"] == 5
    assert second.idempotent_replay is True
    assert len([entry for entry in journal.entries() if entry.type == "action_started"]) == 1
    assert journal.verify_chain()


def test_idempotency_key_cannot_bind_a_different_request():
    executor = ActionExecutor(ToolRegistry.deterministic())
    first = request(operation="add", values=[1, 2]).model_copy(update={"idempotency_key": "same-key"})
    executor.execute(first, granted_permissions={"compute"})
    conflicting = first.model_copy(update={"parameters": {"operation": "multiply", "values": [2, 3]}})
    with pytest.raises(ActionRejected, match="idempotency key"):
        executor.execute(conflicting, granted_permissions={"compute"})


def test_unregistered_tool_is_rejected_by_default():
    executor = ActionExecutor(ToolRegistry.deterministic())
    result = executor.execute(request("not_registered", value=1), granted_permissions={"compute"})
    assert result.status == "rejected"
    assert "not registered" in (result.error or "")


def test_missing_permission_is_rejected_without_handler_execution():
    executor = ActionExecutor(ToolRegistry.deterministic())
    result = executor.execute(request(operation="add", values=[1, 2]))
    assert result.status == "rejected"
    assert "permissions" in (result.error or "")


def test_write_requires_explicit_approval_and_workspace_is_confined(tmp_path):
    executor = ActionExecutor(ToolRegistry.deterministic(workspace_root=tmp_path))
    action = request("write_workspace", path="result.txt", content="safe")
    with pytest.raises(ApprovalRequired):
        executor.execute(action, granted_permissions={"workspace.write"})
    completed = executor.execute(action, granted_permissions={"workspace.write"}, approval=True)
    assert completed.status == "succeeded"
    assert (tmp_path / "result.txt").read_text() == "safe"
    traversal = executor.execute(request("write_workspace", path="../escape.txt", content="unsafe"), granted_permissions={"workspace.write"}, approval=True)
    assert traversal.status == "rejected"
    assert not (tmp_path.parent / "escape.txt").exists()


def test_invalid_parameters_and_budget_are_rejected():
    executor = ActionExecutor(ToolRegistry.deterministic())
    invalid = executor.execute(request(operation="add", values=[True]), granted_permissions={"compute"})
    assert invalid.status in {"rejected", "failed"}
    too_low = executor.execute(
        ActionRequest(
            mission_id=uuid4(), plan_id=uuid4(), step_id=uuid4(), tool_name="calculate",
            parameters={"operation": "add", "values": [1, 2]}, idempotency_key=f"low-{uuid4()}", budget_usd=0.0,
        ), granted_permissions={"compute"}, budget_remaining_usd=0.0,
    )
    assert too_low.status == "rejected"


def test_uncertain_tool_result_is_persisted_without_replay():
    executor = ActionExecutor(ToolRegistry.deterministic())
    action = request("simulated_uncertain", reason="transport interrupted")
    result = executor.execute(action, granted_permissions={"demo.simulate"})
    replay = executor.execute(action, granted_permissions={"demo.simulate"})
    assert result.status == "uncertain"
    assert replay.idempotent_replay is True
    assert executor.get(action.action_id).status == "uncertain"


def test_cognitive_engine_controls_registered_action_and_verification():
    executor = ActionExecutor(ToolRegistry.deterministic())
    engine = CognitiveEngine(plan_engine=PlanEngine(), action_executor=executor)
    goal = GoalUnderstanding(
        objective="calculate a bounded result",
        expected_results=["calculation"],
        success_criteria=["ok is observed"],
        constraints={"budget_usd": 2.0},
    )
    cycle = engine.start(goal, action_tool="calculate")
    plan = engine.plan_engine.get_plan(cycle.plan_id)
    step = plan.steps[0]
    action = ActionRequest(
        mission_id=cycle.mission.mission_id,
        plan_id=cycle.plan_id,
        step_id=step.step_id,
        tool_name="calculate",
        parameters={"operation": "add", "values": [4, 6]},
        idempotency_key="cognitive-calculate-once",
        budget_usd=2.0,
    )
    result = engine.execute_action(cycle.cycle_id, step.step_id, action, granted_permissions={"compute"})
    assert result.status == "succeeded"
    assert engine.get_cycle(cycle.cycle_id).status == "succeeded"
    assert engine.plan_engine.get_plan(cycle.plan_id).all_verified


def test_persistent_runtime_restores_action_record_without_replay(tmp_path):
    store = FileSnapshotStore(tmp_path / "runtime.json")
    runtime = PersistentRuntime(store)
    mission_id, plan_id, step_id = uuid4(), uuid4(), uuid4()
    action = ActionRequest(
        mission_id=mission_id, plan_id=plan_id, step_id=step_id,
        tool_name="calculate", parameters={"operation": "add", "values": [1, 2]},
        idempotency_key="persisted-action", budget_usd=1.0,
    )
    first = runtime.action_executor.execute(action, granted_permissions={"compute"})
    restarted = PersistentRuntime(store)
    replay = restarted.action_executor.execute(action, granted_permissions={"compute"})
    assert first.status == "succeeded"
    assert replay.idempotent_replay is True
    assert restarted.journal.verify_chain()
