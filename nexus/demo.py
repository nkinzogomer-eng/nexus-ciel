"""Runnable smoke demo for the synthetic provider cascade.

The demo explicitly supplies a deterministic oracle because its providers are
fixtures. It is not evidence of production model or tool execution.
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
            SecondaryProvider(confidence=secondary_confidence),
            LocalProvider(confidence=local_confidence, available=local_available),
        ]
    )
    runtime = NexusRuntime(router=router)
    mission = Mission(
        objective=objective,
        constraints={
            "verification": {
                "mode": "contains_any",
                "needles": ["local:", "secondary:"],
            }
        },
    )
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
        "output": report.output,
        "cost_usd": report.cost_usd,
        "cost_avoided_usd": router.total_cost_avoided_usd,
        "trace": report.actions,
        "journal_chain_valid": runtime.journal.verify_chain(),
        "journal_entries": [entry.type for entry in runtime.journal.entries()],
        "events": [event.type for event in runtime.bus.events],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Nexus Ciel synthetic-provider smoke demo")
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
