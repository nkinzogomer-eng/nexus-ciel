"""Controlled offline demonstration of planning, scoped tools, fallback, and proof."""
from __future__ import annotations

import asyncio
import json

from nexus.core import NexusRuntime
from nexus.core.tool_registry import ToolSpec
from nexus.providers import LocalProvider
from nexus.router import AdaptiveRouter
from nexus.schemas import Mission


async def run() -> dict[str, object]:
    runtime = NexusRuntime(router=AdaptiveRouter([LocalProvider(confidence=0.95)]))
    attempts = {"primary": 0}

    def primary_lookup(_arguments: dict[str, object]) -> dict[str, str]:
        attempts["primary"] += 1
        raise RuntimeError("controlled fixture outage")

    def fallback_lookup(_arguments: dict[str, object]) -> dict[str, str]:
        return {"item": "recovered item", "source": "demo fixture"}

    runtime.tool_registry.register(
        ToolSpec("demo-primary-lookup", primary_lookup, frozenset({"catalog:read"}))
    )
    runtime.tool_registry.register(
        ToolSpec("demo-fallback-lookup", fallback_lookup, frozenset({"catalog:read"}))
    )
    mission = Mission(
        objective="retrieve and summarize the demo catalog item",
        constraints={
            "plan": [
                {"id": "lookup", "kind": "tool", "tool": "demo-primary-lookup",
                 "fallback_to": "fallback"},
                {"id": "fallback", "kind": "tool", "tool": "demo-fallback-lookup"},
                {"id": "summarize", "kind": "generate", "task": "summarize the retrieved item",
                 "depends_on": ["fallback"]},
            ],
            "allowed_tools": ["demo-primary-lookup", "demo-fallback-lookup"],
            "permissions": ["catalog:read"],
            "verification": {"mode": "contains_all", "needles": ["recovered item", "demo fixture"]},
        },
    )
    mission_id = await runtime.accept(mission)
    report = runtime.report(mission_id)
    state = runtime.state_graph.get(mission.mission_id)
    assert report is not None and state is not None
    return {
        "mission_id": mission_id,
        "state": state.status,
        "verdict": report.verdict,
        "compiled_steps": report.validation.get("compiled_steps", []),
        "actions": report.actions,
        "controlled_primary_failures": attempts["primary"],
        "output": report.output,
        "verification_evidence": report.validation.get("verification"),
        "journal_chain_valid": runtime.journal.verify_chain(),
        "journal_events": [entry.type for entry in runtime.journal.entries()],
        "report": report.model_dump(mode="json"),
    }


def main() -> int:
    result = asyncio.run(run())
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["verdict"] == "PASS" and result["journal_chain_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
