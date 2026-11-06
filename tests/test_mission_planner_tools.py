from uuid import UUID

import pytest

from nexus.core import NexusRuntime
from nexus.core.tool_registry import ToolSpec
from nexus.providers import LocalProvider
from nexus.router import AdaptiveRouter
from nexus.schemas import Mission


@pytest.mark.asyncio
async def test_compiled_mission_recovers_from_controlled_tool_error_and_verifies_evidence():
    runtime = NexusRuntime(router=AdaptiveRouter([LocalProvider(confidence=0.95)]))
    calls = {"primary": 0, "fallback": 0}

    def primary(_args):
        calls["primary"] += 1
        raise RuntimeError("simulated transient catalog outage")

    def fallback(_args):
        calls["fallback"] += 1
        return {"item": "recovered item", "source": "fixture-catalog"}

    runtime.tool_registry.register(ToolSpec("catalog-primary", primary, frozenset({"catalog:read"})))
    runtime.tool_registry.register(ToolSpec("catalog-fallback", fallback, frozenset({"catalog:read"})))
    mission = Mission(
        objective="retrieve and summarize the catalog item",
        constraints={
            "plan": [
                {"id": "lookup", "kind": "tool", "tool": "catalog-primary",
                 "arguments": {}, "fallback_to": "fallback"},
                {"id": "fallback", "kind": "tool", "tool": "catalog-fallback", "arguments": {}},
                {"id": "summarize", "kind": "generate", "task": "summarize retrieved item",
                 "depends_on": ["fallback"]},
            ],
            "allowed_tools": ["catalog-primary", "catalog-fallback"],
            "permissions": ["catalog:read"],
            "verification": {"mode": "contains_all", "needles": ["recovered item", "fixture-catalog"]},
            "max_iterations": 4,
        },
    )

    mission_id = await runtime.accept(mission)
    report = runtime.report(mission_id)
    assert report is not None
    assert report.verdict == "PASS"
    assert report.iterations == 3
    assert "recovered item" in report.output
    assert calls == {"primary": 1, "fallback": 1}
    assert any(action.get("status") == "replanned" for action in report.actions)
    assert "mission_replanned" in [entry.type for entry in runtime.journal.entries()]
    assert runtime.journal.verify_chain()
    assert runtime.state_graph.get(UUID(mission_id)).status == "validated"


@pytest.mark.asyncio
async def test_tool_requires_mission_allowlist_and_exact_permission_scope():
    runtime = NexusRuntime()
    runtime.tool_registry.register(ToolSpec("private-read", lambda _args: "secret", frozenset({"private:read"})))
    mission = Mission(
        objective="read private data",
        constraints={"plan": [{"id": "read", "kind": "tool", "tool": "private-read"}],
                     "allowed_tools": ["private-read"], "permissions": []},
    )
    mission_id = await runtime.accept(mission)
    report = runtime.report(mission_id)
    assert report is not None and report.verdict == "FAIL"
    assert "lacks permissions" in report.summary


@pytest.mark.asyncio
async def test_side_effecting_or_non_idempotent_tool_is_rejected_at_registration():
    runtime = NexusRuntime()
    with pytest.raises(ValueError, match="read_only, idempotent"):
        runtime.tool_registry.register(ToolSpec("unsafe-write", lambda _args: None, risk="write", idempotent=False))


@pytest.mark.asyncio
async def test_iteration_limit_stops_plan_before_unbounded_work():
    runtime = NexusRuntime(router=AdaptiveRouter([LocalProvider(confidence=0.95)]))
    mission = Mission(
        objective="bounded work",
        constraints={"plan": [
            {"id": "one", "kind": "generate", "task": "one"},
            {"id": "two", "kind": "generate", "task": "two"},
        ], "max_iterations": 1},
    )
    mission_id = await runtime.accept(mission)
    report = runtime.report(mission_id)
    assert report is not None and report.verdict == "FAIL"
    assert report.iterations == 1
    assert report.guard_events[0]["type"] == "iteration_limit"


def test_mission_limits_cannot_raise_above_system_maxima():
    from nexus.core.mission_guard import MissionGuard, MissionGuardViolation

    with pytest.raises(MissionGuardViolation, match="system maximum"):
        MissionGuard().execution_limits(Mission(objective="too long", constraints={"deadline_seconds": 301}))


@pytest.mark.asyncio
async def test_reusable_offline_autonomy_demo_produces_evidence_backed_pass():
    from nexus.autonomy_demo import run

    result = await run()
    assert result["verdict"] == "PASS"
    assert result["state"] == "validated"
    assert result["controlled_primary_failures"] == 1
    assert result["journal_chain_valid"] is True
    assert "mission_replanned" in result["journal_events"]
