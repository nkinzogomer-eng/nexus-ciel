from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from nexus.core.mission_journal import MissionJournal
from nexus.persistence import FileSnapshotStore, PersistentRuntime
from nexus.planning import (
    ConcurrentPlanModification,
    DeterministicCondition,
    InvalidPlanTransition,
    PlanEngine,
    PlanValidationError,
    PostconditionNotMet,
    PreconditionNotMet,
    Step,
    StepBudgetExceeded,
)
from nexus.schemas import Mission


def make_step(*, title="step", ordinal=1, depends_on=None, pre=None, post=None, budget=1.0):
    return Step(
        title=title,
        ordinal=ordinal,
        action_ref=f"deterministic:{title}",
        depends_on=depends_on or [],
        preconditions=pre or [],
        postconditions=post or [],
        idempotency_key=f"key-{title}-{ordinal}",
        budget_usd=budget,
    )


def new_engine():
    return PlanEngine(journal=MissionJournal())


def test_three_dependent_steps_reach_verified_plan():
    mission_id = uuid4()
    first = make_step(title="first", ordinal=1, post=[DeterministicCondition(key="first", expected=True)])
    second = make_step(title="second", ordinal=2, depends_on=[first.step_id])
    third = make_step(title="third", ordinal=3, depends_on=[second.step_id])
    engine = new_engine()
    plan = engine.create_plan(mission_id, [first, second, third], budget_usd=3.0)
    plan = engine.validate_plan(plan.plan_id)
    for step in [first, second, third]:
        plan = engine.make_step_ready(plan.plan_id, step.step_id, {})
        plan = engine.start_step(plan.plan_id, step.step_id, estimated_cost_usd=1.0)
        observation = {"first": True} if step.step_id == first.step_id else {}
        plan = engine.record_observation(plan.plan_id, step.step_id, observation, actual_cost_usd=1.0)
        plan = engine.verify_step(plan.plan_id, step.step_id)
    assert plan.status == "succeeded"
    assert all(step.status == "verified" for step in plan.steps)
    assert [entry.type for entry in engine.journal.entries()] == [
        "plan_created", "plan_validated", "step_ready", "step_started",
        "observation_added", "step_verified", "step_ready", "step_started",
        "observation_added", "step_verified", "step_ready", "step_started",
        "observation_added", "step_verified",
    ]


def test_failed_step_is_terminal_for_plan_until_explicit_revision():
    engine = new_engine()
    step = make_step()
    plan = engine.validate_plan(engine.create_plan(uuid4(), [step], budget_usd=1.0).plan_id)
    plan = engine.make_step_ready(plan.plan_id, step.step_id, {})
    plan = engine.fail_step(plan.plan_id, step.step_id, "deterministic failure")
    assert plan.status == "failed"
    with pytest.raises(InvalidPlanTransition):
        engine.start_step(plan.plan_id, step.step_id)


def test_unsatisfied_precondition_is_rejected_without_mutation():
    engine = new_engine()
    step = make_step(pre=[DeterministicCondition(key="approved", expected=True)])
    plan = engine.validate_plan(engine.create_plan(uuid4(), [step], budget_usd=1.0).plan_id)
    with pytest.raises(PreconditionNotMet):
        engine.make_step_ready(plan.plan_id, step.step_id, {"approved": False})
    assert engine.get_plan(plan.plan_id).steps[0].status == "planned"


def test_circular_dependency_is_rejected():
    first = make_step(title="first", ordinal=1)
    second = make_step(title="second", ordinal=2, depends_on=[first.step_id])
    first = first.model_copy(update={"depends_on": [second.step_id]})
    with pytest.raises(PlanValidationError, match="cycle"):
        new_engine().create_plan(uuid4(), [first, second], budget_usd=2.0)


def test_plan_persists_and_restores_with_progress_and_journal(tmp_path):
    store = FileSnapshotStore(tmp_path / "runtime.json")
    mission = Mission(objective="persist plan")
    runtime = PersistentRuntime(store)
    step = make_step()
    plan = runtime.plan_engine.create_plan(mission.mission_id, [step], budget_usd=1.0)
    runtime.plan_engine.validate_plan(plan.plan_id)
    runtime.plan_engine.make_step_ready(plan.plan_id, step.step_id, {})
    runtime.plan_engine.revise_plan(
        plan.plan_id,
        [make_step(title="revised")],
        expected_version=1,
        rationale="persist revision history",
        budget_usd=1.0,
    )
    restarted = PersistentRuntime(store)
    restored = restarted.plan_engine.get_plan(plan.plan_id)
    assert restored.version == 2
    assert restored.status == "draft"
    assert restored.steps[0].title == "revised"
    assert len(restarted.plan_engine.history(plan.plan_id)) == 2
    assert restarted.journal.entries(mission.mission_id)[-1].type == "plan_revised"
    assert restarted.journal.verify_chain()


def test_revision_after_observation_is_append_only_and_keeps_history():
    engine = new_engine()
    step = make_step(post=[DeterministicCondition(key="ok", expected=True)])
    plan = engine.validate_plan(engine.create_plan(uuid4(), [step], budget_usd=1.0).plan_id)
    engine.make_step_ready(plan.plan_id, step.step_id, {})
    engine.start_step(plan.plan_id, step.step_id, estimated_cost_usd=1.0)
    engine.record_observation(plan.plan_id, step.step_id, {"ok": True}, actual_cost_usd=1.0)
    revised = engine.revise_plan(
        plan.plan_id,
        [make_step(title="replacement")],
        expected_version=1,
        rationale="observation requires a safer plan",
        budget_usd=1.0,
    )
    assert revised.version == 2
    assert revised.status == "draft"
    assert len(engine.history(plan.plan_id)) == 2
    assert engine.history(plan.plan_id)[0].steps[0].status == "observed"


def test_max_steps_and_budget_are_enforced():
    too_many = [make_step(title=f"s{i}", ordinal=i) for i in range(1, 4)]
    with pytest.raises(PlanValidationError, match="max_steps"):
        new_engine().create_plan(uuid4(), too_many, budget_usd=3.0, max_steps=2)
    engine = new_engine()
    step = make_step(budget=0.5)
    plan = engine.validate_plan(engine.create_plan(uuid4(), [step], budget_usd=0.5).plan_id)
    plan = engine.make_step_ready(plan.plan_id, step.step_id, {})
    with pytest.raises(StepBudgetExceeded):
        engine.start_step(plan.plan_id, step.step_id, estimated_cost_usd=0.6)


def test_postcondition_failure_is_recorded_and_rejected():
    engine = new_engine()
    step = make_step(post=[DeterministicCondition(key="verified", expected=True)])
    plan = engine.validate_plan(engine.create_plan(uuid4(), [step], budget_usd=1.0).plan_id)
    engine.make_step_ready(plan.plan_id, step.step_id, {})
    engine.start_step(plan.plan_id, step.step_id, estimated_cost_usd=1.0)
    engine.record_observation(plan.plan_id, step.step_id, {"verified": False}, actual_cost_usd=1.0)
    with pytest.raises(PostconditionNotMet):
        engine.verify_step(plan.plan_id, step.step_id)
    assert engine.get_plan(plan.plan_id).status == "failed"


def test_concurrent_revision_attempts_allow_only_one_writer():
    engine = new_engine()
    plan = engine.create_plan(uuid4(), [make_step()], budget_usd=1.0)

    def revise(title):
        try:
            return ("ok", engine.revise_plan(
                plan.plan_id,
                [make_step(title=title)],
                expected_version=1,
                rationale=title,
                budget_usd=1.0,
            ))
        except ConcurrentPlanModification:
            return ("conflict", None)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(revise, ["writer-a", "writer-b"]))
    assert [result[0] for result in results].count("ok") == 1
    assert [result[0] for result in results].count("conflict") == 1
