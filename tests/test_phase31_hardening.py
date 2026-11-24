from uuid import uuid4

import pytest

from nexus.cognitive import ControlledReplanner, CognitiveEngine, GoalUnderstanding
from nexus.core.mission_journal import MissionJournal
from nexus.persistence import FileSnapshotStore, PersistentRuntime
from nexus.planning import (
    DeterministicCondition,
    InvalidPlanTransition,
    PlanEngine,
    PreconditionNotMet,
    Step,
    StepBudgetExceeded,
)


def chain_steps(count=3, budget=1.0):
    steps = [
        Step(
            ordinal=index,
            title=f"step-{index}",
            action_ref=f"test.action.{index}",
            idempotency_key=f"test-key-{index}",
            budget_usd=budget,
            postconditions=[DeterministicCondition(key="ok", expected=True)],
        )
        for index in range(1, count + 1)
    ]
    return [
        step.model_copy(update={"depends_on": [steps[index - 2].step_id] if index > 1 else []})
        for index, step in enumerate(steps, start=1)
    ]


def execute_success(engine, plan_id, step, cost=0.1):
    engine.make_step_ready(plan_id, step.step_id, {})
    engine.start_step(plan_id, step.step_id, estimated_cost_usd=cost)
    engine.record_observation(plan_id, step.step_id, {"ok": True}, actual_cost_usd=cost)
    return engine.verify_step(plan_id, step.step_id)


def test_first_failure_preserves_remaining_steps_and_resumes_after_correction():
    engine = PlanEngine()
    steps = chain_steps()
    plan = engine.validate_plan(engine.create_plan(uuid4(), steps, budget_usd=6.0).plan_id)
    engine.make_step_ready(plan.plan_id, steps[0].step_id, {})
    engine.fail_step(plan.plan_id, steps[0].step_id, "first failure")
    revised = ControlledReplanner().revise_after_failure(engine, plan.plan_id, reason="repair first step")
    assert {step.title for step in revised.steps} == {"step-2", "step-3", "controlled-correction"}
    correction = next(step for step in revised.steps if step.title == "controlled-correction")
    step2 = next(step for step in revised.steps if step.title == "step-2")
    step3 = next(step for step in revised.steps if step.title == "step-3")
    assert step2.depends_on == [correction.step_id]
    assert step3.depends_on == [step2.step_id]
    execute_success(engine, revised.plan_id, correction)
    execute_success(engine, revised.plan_id, step2)
    completed = execute_success(engine, revised.plan_id, step3)
    assert completed.status == "succeeded"


def test_intermediate_failure_preserves_verified_prefix_and_suffix():
    engine = PlanEngine()
    steps = chain_steps()
    plan = engine.validate_plan(engine.create_plan(uuid4(), steps, budget_usd=6.0).plan_id)
    execute_success(engine, plan.plan_id, steps[0])
    engine.make_step_ready(plan.plan_id, steps[1].step_id, {})
    engine.fail_step(plan.plan_id, steps[1].step_id, "middle failure")
    revised = ControlledReplanner().revise_after_failure(engine, plan.plan_id, reason="repair middle step")
    assert any(step.step_id == steps[0].step_id and step.status == "verified" for step in revised.steps)
    assert any(step.step_id == steps[2].step_id for step in revised.steps)
    correction = next(step for step in revised.steps if step.title == "controlled-correction")
    suffix = next(step for step in revised.steps if step.step_id == steps[2].step_id)
    assert suffix.depends_on == [correction.step_id]


def test_failed_correction_stays_failed_and_is_not_replayed():
    engine = PlanEngine()
    steps = chain_steps()
    plan = engine.validate_plan(engine.create_plan(uuid4(), steps, budget_usd=6.0).plan_id)
    engine.make_step_ready(plan.plan_id, steps[0].step_id, {})
    engine.fail_step(plan.plan_id, steps[0].step_id, "first failure")
    revised = ControlledReplanner().revise_after_failure(engine, plan.plan_id, reason="repair")
    correction = next(step for step in revised.steps if step.title == "controlled-correction")
    engine.make_step_ready(revised.plan_id, correction.step_id, {})
    failed = engine.fail_step(revised.plan_id, correction.step_id, "correction failed")
    assert failed.status == "failed"
    with pytest.raises(InvalidPlanTransition):
        engine.start_step(revised.plan_id, correction.step_id)


def test_no_budget_for_correction_is_rejected():
    engine = PlanEngine()
    steps = chain_steps(budget=1.0)
    plan = engine.validate_plan(engine.create_plan(uuid4(), steps, budget_usd=3.0).plan_id)
    engine.make_step_ready(plan.plan_id, steps[0].step_id, {})
    engine.start_step(plan.plan_id, steps[0].step_id, estimated_cost_usd=1.0)
    engine.record_observation(plan.plan_id, steps[0].step_id, {"ok": False}, actual_cost_usd=1.0)
    engine.fail_step(plan.plan_id, steps[0].step_id, "failed")
    with pytest.raises(ValueError, match="budget"):
        ControlledReplanner().revise_after_failure(engine, plan.plan_id, reason="no room")


def test_uncertain_observation_is_suspended_and_never_replayed():
    runtime = CognitiveEngine(plan_engine=PlanEngine())
    goal = GoalUnderstanding(
        objective="verify a result",
        expected_results=["result"],
        success_criteria=["ok is observed"],
        constraints={"budget_usd": 2.0},
    )
    cycle = runtime.start(goal)
    step = runtime.plan_engine.get_plan(cycle.plan_id).steps[0]
    runtime.plan_engine.make_step_ready(cycle.plan_id, step.step_id, {})
    runtime.plan_engine.start_step(cycle.plan_id, step.step_id, estimated_cost_usd=0.1)
    assessment = runtime.observe(cycle.cycle_id, step.step_id, {}, actual_cost_usd=0.1, outcome="uncertain")
    assert assessment.outcome == "uncertain"
    assert runtime.plan_engine.get_plan(cycle.plan_id).steps[0].status == "uncertain"
    with pytest.raises(InvalidPlanTransition):
        runtime.plan_engine.start_step(cycle.plan_id, step.step_id)


def test_partial_observation_is_not_success():
    runtime = CognitiveEngine(plan_engine=PlanEngine())
    goal = GoalUnderstanding(
        objective="verify a result",
        expected_results=["result"],
        success_criteria=["ok is observed"],
        constraints={"budget_usd": 2.0},
    )
    cycle = runtime.start(goal)
    step = runtime.plan_engine.get_plan(cycle.plan_id).steps[0]
    runtime.plan_engine.make_step_ready(cycle.plan_id, step.step_id, {})
    runtime.plan_engine.start_step(cycle.plan_id, step.step_id, estimated_cost_usd=0.1)
    assessment = runtime.observe(cycle.cycle_id, step.step_id, {"partial": True}, actual_cost_usd=0.1, outcome="partial")
    assert assessment.outcome == "partial"
    assert runtime.get_cycle(cycle.cycle_id).status == "suspended"


def test_reserved_and_actual_costs_are_distinct():
    engine = PlanEngine()
    step = chain_steps(1, budget=1.0)[0]
    plan = engine.validate_plan(engine.create_plan(uuid4(), [step], budget_usd=1.0).plan_id)
    engine.make_step_ready(plan.plan_id, step.step_id, {})
    running = engine.start_step(plan.plan_id, step.step_id, estimated_cost_usd=0.4)
    assert running.total_reserved_cost_usd == 0.4
    observed = engine.record_observation(plan.plan_id, step.step_id, {"ok": True}, actual_cost_usd=0.3)
    assert observed.total_reserved_cost_usd == 0.0
    assert observed.total_spent_cost_usd == 0.3


def test_precondition_rejection_is_journaled():
    journal = MissionJournal()
    engine = PlanEngine(journal=journal)
    step = chain_steps(1)[0].model_copy(
        update={"preconditions": [DeterministicCondition(key="approved", expected=True)]}
    )
    plan = engine.validate_plan(engine.create_plan(uuid4(), [step], budget_usd=1.0).plan_id)
    with pytest.raises(PreconditionNotMet):
        engine.make_step_ready(plan.plan_id, step.step_id, {"approved": False})
    assert journal.entries()[-1].type == "step_blocked"


def test_replanned_history_restores_after_restart(tmp_path):
    store = FileSnapshotStore(tmp_path / "runtime.json")
    runtime = PersistentRuntime(store)
    steps = chain_steps()
    plan = runtime.plan_engine.validate_plan(runtime.plan_engine.create_plan(uuid4(), steps, budget_usd=6.0).plan_id)
    runtime.plan_engine.make_step_ready(plan.plan_id, steps[0].step_id, {})
    runtime.plan_engine.fail_step(plan.plan_id, steps[0].step_id, "failed")
    revised = ControlledReplanner().revise_after_failure(runtime.plan_engine, plan.plan_id, reason="repair")
    restarted = PersistentRuntime(store)
    assert restarted.plan_engine.get_plan(plan.plan_id).version == revised.version
    assert len(restarted.plan_engine.history(plan.plan_id)) == 2
    assert {step.title for step in restarted.plan_engine.get_plan(plan.plan_id).steps} >= {"step-2", "step-3"}
