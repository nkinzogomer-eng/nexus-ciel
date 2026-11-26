import pytest

from nexus.cognitive import CognitiveEngine, GoalInputAnalysis, MissionCompilationError, NaturalGoalInterpreter, MissionCompiler
from nexus.planning import PlanEngine


def test_natural_goal_is_bounded_and_preserves_fact_hypothesis_unknown_and_decision():
    analysis = NaturalGoalInterpreter().interpret(
        "Calcule le résultat, sachant que base=4, supposons que la valeur soit stable, "
        "il manque la date, vérifie que le résultat vaut 10, budget 1.5"
    )

    assert isinstance(analysis, GoalInputAnalysis)
    assert analysis.status == "accepted"
    assert analysis.known_facts == {"base": 4}
    assert analysis.hypotheses[0].statement == "la valeur soit stable"
    assert analysis.unknowns == ["la date"]
    assert analysis.explicit_constraints["budget_usd"] == 1.5
    assert analysis.explicit_constraints["expected_observations"] == {"result": 10}
    assert analysis.decisions
    goal = analysis.to_goal()
    compiled = MissionCompiler().compile(goal)
    assert compiled.assumptions[0].statement == "la valeur soit stable"
    assert "la date" in compiled.missing_information


def test_non_blocking_unknown_is_not_a_clarification_request():
    analysis = NaturalGoalInterpreter().interpret(
        "Calcule un résultat ; il manque la date ; budget 1"
    )
    assert analysis.status == "accepted"
    assert analysis.blocking_questions == []


def test_sensitive_action_without_target_is_blocked_but_not_silently_assumed():
    analysis = NaturalGoalInterpreter().interpret("Écris le résultat avec budget 1")
    assert analysis.status == "needs_clarification"
    assert "workspace target path" in analysis.blocking_questions
    assert "write_workspace" in analysis.approval_required_tools
    assert analysis.to_goal().constraints["approval_required_tools"] == ["write_workspace"]


def test_explicit_contradiction_is_blocking():
    analysis = NaturalGoalInterpreter().interpret("Calcule le résultat, contradiction: résultat impossible")
    assert analysis.status == "needs_clarification"
    assert analysis.contradictions
    assert analysis.blocking_questions == ["contradictory requirement"]


def test_cognitive_engine_natural_entrypoint_does_not_guess_blocking_input():
    engine = CognitiveEngine(plan_engine=PlanEngine())
    cycle = engine.start_natural("Calcule 2 + 3 avec budget 1")
    assert cycle.mode == "CORE_ONLY"
    with pytest.raises(MissionCompilationError, match="clarification required"):
        engine.start_natural("Écris le résultat avec budget 1")
