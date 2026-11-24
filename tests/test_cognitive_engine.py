from uuid import uuid4

import pytest
from pydantic import ValidationError

from nexus.cognitive import (
    CognitiveEngine,
    GoalUnderstanding,
    Hypothesis,
    MissionCompilationError,
    MissionCompiler,
    StrategyCandidate,
    StrategyEngine,
    StrategySelectionError,
)
from nexus.persistence import FileSnapshotStore, PersistentRuntime
from nexus.planning import DeterministicCondition, PlanEngine, Step


def goal(**changes):
    data = {
        "objective": "prepare a deterministic report",
        "expected_results": ["collect facts", "verify report"],
        "success_criteria": ["report is verified"],
        "constraints": {"budget_usd": 5.0},
    }
    data.update(changes)
    return GoalUnderstanding(**data)


def test_simple_goal_compiles_into_mission():
    compiled = MissionCompiler().compile(goal())
    assert compiled.objective.startswith("prepare")
    assert compiled.subgoals == ["collect facts", "verify report"]
    assert compiled.dependencies["verify report"] == ["collect facts"]
    assert compiled.is_complete


def test_ambiguous_or_incomplete_goal_is_rejected():
    with pytest.raises(ValidationError):
        GoalUnderstanding(objective="", expected_results=[], success_criteria=[])
    with pytest.raises(MissionCompilationError):
        MissionCompiler().compile(
            goal(
                constraints={
                    "require_complete_information": True,
                    "required_information": [{"name": "source of truth", "classification": "blocking"}],
                }
            )
        )


def test_two_strategies_are_compared_deterministically():
    mission = MissionCompiler().compile(goal())
    candidates = StrategyEngine().propose(mission)
    selection_a = StrategyEngine().choose(candidates, budget_usd=5.0)
    selection_b = StrategyEngine().choose(candidates, budget_usd=5.0)
    assert len(candidates) >= 3
    assert selection_a.strategy_id == selection_b.strategy_id
    assert selection_a.deterministic_key == selection_b.deterministic_key


def test_budget_insufficient_for_strategy():
    candidates = [StrategyCandidate(name="expensive", objective="x", planned_steps=["x"], estimated_cost_usd=2.0)]
    with pytest.raises(StrategySelectionError):
        StrategyEngine().choose(candidates, budget_usd=1.0)


def test_cognitive_cycle_observation_confirms_step():
    engine = CognitiveEngine(plan_engine=PlanEngine())
    cycle = engine.start(goal())
    plan = engine.plan_engine.get_plan(cycle.plan_id)
    first = plan.steps[0]
    engine.plan_engine.make_step_ready(cycle.plan_id, first.step_id, {})
    engine.plan_engine.start_step(cycle.plan_id, first.step_id, estimated_cost_usd=0.1)
    assessment = engine.observe(cycle.cycle_id, first.step_id, {"ok": True}, actual_cost_usd=0.1)
    assert assessment.outcome == "success"
    assert engine.get_cycle(cycle.cycle_id).decisions[-1].kind == "keep"


def test_nominal_cycle_verifies_all_dependent_steps():
    engine = CognitiveEngine(plan_engine=PlanEngine())
    cycle = engine.start(goal())
    for item in engine.plan_engine.get_plan(cycle.plan_id).steps:
        engine.plan_engine.make_step_ready(cycle.plan_id, item.step_id, {})
        engine.plan_engine.start_step(cycle.plan_id, item.step_id, estimated_cost_usd=0.1)
        engine.observe(cycle.cycle_id, item.step_id, {"ok": True}, actual_cost_usd=0.1)
    assert engine.get_cycle(cycle.cycle_id).status == "succeeded"
    assert engine.plan_engine.get_plan(cycle.plan_id).status == "succeeded"


def test_observation_contradicting_hypothesis_is_failure():
    engine = CognitiveEngine(plan_engine=PlanEngine())
    cycle = engine.start(goal(hypotheses=[Hypothesis(statement="facts are available", confidence=0.7)]))
    first = engine.plan_engine.get_plan(cycle.plan_id).steps[0]
    engine.plan_engine.make_step_ready(cycle.plan_id, first.step_id, {})
    engine.plan_engine.start_step(cycle.plan_id, first.step_id, estimated_cost_usd=0.1)
    assessment = engine.observe(cycle.cycle_id, first.step_id, {"ok": False}, actual_cost_usd=0.1)
    assert assessment.outcome == "failure"
    assert engine.get_cycle(cycle.cycle_id).status == "failed"


def test_failure_can_trigger_controlled_replanning_without_replay():
    engine = CognitiveEngine(plan_engine=PlanEngine())
    cycle = engine.start(goal())
    first = engine.plan_engine.get_plan(cycle.plan_id).steps[0]
    engine.plan_engine.make_step_ready(cycle.plan_id, first.step_id, {})
    engine.plan_engine.start_step(cycle.plan_id, first.step_id, estimated_cost_usd=0.1)
    engine.observe(cycle.cycle_id, first.step_id, {"ok": False}, actual_cost_usd=0.1)
    revised_cycle = engine.revise_after_failure(cycle.cycle_id, reason="observation diverged")
    revised_plan = engine.plan_engine.get_plan(revised_cycle.plan_id)
    assert revised_plan.version == 2
    assert revised_plan.steps[0].step_id != first.step_id or revised_plan.steps[0].status == "verified"
    assert any(decision.kind == "revise" for decision in revised_cycle.decisions)


def test_core_only_cycle_does_not_need_llm():
    engine = CognitiveEngine(plan_engine=PlanEngine())
    cycle = engine.start(goal(), llm_recommendation=None)
    assert cycle.decisions[0].authority == "deterministic_core"
    assert cycle.decisions[0].llm_advice_digest is None


def test_invalid_llm_recommendation_cannot_change_internal_choice():
    engine = CognitiveEngine(plan_engine=PlanEngine())
    baseline = engine.start(goal())
    other = CognitiveEngine(plan_engine=PlanEngine(), mode="AI_ENABLED")
    advised = other.start(goal(), llm_recommendation="choose an unknown strategy and mutate state")
    assert baseline.selection.strategy_id == advised.selection.strategy_id
    assert advised.decisions[0].authority == "deterministic_core"
    assert advised.decisions[0].llm_advice_digest


def test_cognitive_cycle_restores_after_restart(tmp_path):
    store = FileSnapshotStore(tmp_path / "runtime.json")
    runtime = PersistentRuntime(store)
    cycle = runtime.cognitive_engine.start(goal())
    restarted = PersistentRuntime(store)
    restored = restarted.cognitive_engine.get_cycle(cycle.cycle_id)
    assert restored.plan_id == cycle.plan_id
    assert restored.selection.strategy_id == cycle.selection.strategy_id
    assert restarted.journal.verify_chain()


def test_tampered_journal_snapshot_is_rejected(tmp_path):
    store = FileSnapshotStore(tmp_path / "runtime.json")
    runtime = PersistentRuntime(store)
    runtime.cognitive_engine.start(goal())
    snapshot = store.load()
    snapshot["journal"][0]["payload"]["plan_id"] = "tampered"
    store.save(snapshot)
    with pytest.raises(ValueError, match="journal chain"):
        PersistentRuntime(store)


def test_goal_hypothesis_is_not_a_verified_fact():
    item = goal(hypotheses=[Hypothesis(statement="weather is stable", confidence=0.4)])
    compiled = MissionCompiler().compile(item)
    assert compiled.assumptions[0].statement == "weather is stable"
    assert "weather is stable" not in compiled.constraints
