"""Runnable smoke demo: prove Nexus Ciel does something end to end.

    python -m nexus.demo "summarise the sprint"

Runs a real mission through the state graph, the chained journal, the event
bus and the economic cascade, then prints the report and the escalation trace.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from uuid import UUID

from nexus.core import NexusRuntime
from nexus.providers import LocalProvider, SecondaryProvider
from nexus.router import AdaptiveRouter
from nexus.schemas import Mission


async def run(
    objective: str,
    local_confidence: float,
    local_available: bool,
    secondary_confidence: float = 0.90,
) -> dict:
    router = AdaptiveRouter(
        [
            # declared first on purpose: the cascade must reorder it
            SecondaryProvider(confidence=secondary_confidence),
            LocalProvider(confidence=local_confidence, available=local_available),
        ]
    )
    runtime = NexusRuntime(router=router)
    mission = Mission(objective=objective)
    mission_id = await runtime.accept(mission)
    report = runtime.report(mission_id)
    state = runtime.state_graph.get(UUID(mission_id))
    assert report is not None and state is not None
    return {
        "mission_id": mission_id,
        "policy": {
            "source": router.policy.source_path,
            "version": router.policy.version,
            "threshold": router.policy.confidence_threshold,
        },
        "state": state.status,
        "verdict": report.verdict,
        "summary": report.summary,
        "cost_usd": report.cost_usd,
        "cost_avoided_usd": router.total_cost_avoided_usd,
        "trace": report.actions,
        "journal_chain_valid": runtime.journal.verify_chain(),
        "journal_entries": [e.type for e in runtime.journal.entries()],
        "events": [e.type for e in runtime.bus.events],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Nexus Ciel smoke demo")
    parser.add_argument("objective", nargs="?", default="summarise the sprint")
    parser.add_argument("--local-confidence", type=float, default=0.80)
    parser.add_argument("--local-unavailable", action="store_true")
    parser.add_argument(
        "--secondary-confidence",
        type=float,
        default=0.90,
        help="lower it below the policy threshold to exercise the unroutable path",
    )
    args = parser.parse_args(argv)
    out = asyncio.run(
        run(
            args.objective,
            args.local_confidence,
            not args.local_unavailable,
            args.secondary_confidence,
        )
    )
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if out["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
