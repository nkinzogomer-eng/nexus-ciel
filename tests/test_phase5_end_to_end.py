from nexus.actions import ActionExecutor, ActionRequest, ToolRegistry
from nexus.cognitive import CognitiveEngine, NaturalGoalInterpreter
from nexus.planning import PlanEngine


def test_natural_goal_runs_through_real_cognitive_components_in_core_only():
    analysis = NaturalGoalInterpreter().interpret(
        "Calcule la somme 4 et 6, avec budget 1, vérifie que le résultat vaut 10"
    )
    assert analysis.status == "accepted"
    goal = analysis.to_goal()
    executor = ActionExecutor(ToolRegistry.deterministic())
    engine = CognitiveEngine(plan_engine=PlanEngine(), action_executor=executor, mode="CORE_ONLY")

    cycle = engine.start(goal, budget_usd=1.0, action_tool="calculate")
    assert cycle.mode == "CORE_ONLY"
    assert cycle.selection.candidate_name == "staged-verified"
    step = engine.plan_engine.get_plan(cycle.plan_id).steps[0]
    request = ActionRequest(
        mission_id=cycle.mission.mission_id,
        plan_id=cycle.plan_id,
        step_id=step.step_id,
        tool_name="calculate",
        parameters={"operation": "add", "values": [4, 6]},
        idempotency_key="phase5-natural-calculate",
        budget_usd=1.0,
    )
    result = engine.execute_action(cycle.cycle_id, step.step_id, request, granted_permissions={"compute"})

    assert result.status == "succeeded"
    assert result.observation["result"] == 10
    assert engine.get_cycle(cycle.cycle_id).status == "succeeded"
    assert engine.plan_engine.get_plan(cycle.plan_id).all_verified
