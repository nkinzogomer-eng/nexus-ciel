"""Versioned, read-only routing policy.

The policy is *data*, not code: it lives in ``policies/routing_policy_v1.json``,
is owned logically by the Evolution Engine, and the Router may only read it.
This module is the single place allowed to load it.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

OFFICIAL_STAGES: tuple[str, ...] = (
    "cache",
    "memory",
    "formal",
    "tool",
    "small_model",
    "large_model",
    "deep",
)

POLICY_ENV_VAR = "NEXUS_ROUTING_POLICY"
POLICY_FILENAME = "routing_policy_v1.json"
_PACKAGE_ROOT = Path(__file__).resolve().parents[2]


class PolicyError(RuntimeError):
    """Raised when the routing policy is missing, malformed, or not read-only."""


@dataclass(frozen=True)
class RoutingPolicy:
    """Immutable view of the routing policy. Frozen on purpose: the Router owns
    no write path to this object nor to the file it came from."""

    version: int = 1
    confidence_threshold: float = 0.75
    stages: tuple[str, ...] = OFFICIAL_STAGES
    owner: str = "evolution_engine"
    router_access: str = "read_only"
    schema_version: int = 1
    source_path: str | None = None

    @property
    def read_only_for_router(self) -> bool:
        return self.router_access == "read_only"

    def allows(self, stage: str) -> bool:
        return stage in self.stages

    def stage_rank(self, stage: str) -> int:
        """Position of a stage in the official cascade. Unknown stages rank last."""
        try:
            return self.stages.index(stage)
        except ValueError:
            return len(self.stages)


def candidate_paths(explicit: str | os.PathLike[str] | None = None) -> list[Path]:
    if explicit is not None:
        return [Path(explicit)]
    found: list[Path] = []
    from_env = os.environ.get(POLICY_ENV_VAR)
    if from_env:
        found.append(Path(from_env))
    found.append(_PACKAGE_ROOT / "policies" / POLICY_FILENAME)
    found.append(Path.cwd() / "policies" / POLICY_FILENAME)
    return found


def resolve_policy_path(explicit: str | os.PathLike[str] | None = None) -> Path:
    tried = candidate_paths(explicit)
    for path in tried:
        if path.is_file():
            return path
    raise PolicyError(
        "routing policy file not found; looked in: "
        + ", ".join(str(p) for p in tried)
    )


def _validate(data: dict, path: Path) -> None:
    def fail(reason: str) -> None:
        raise PolicyError(f"invalid routing policy at {path}: {reason}")

    required = {
        "schema_version",
        "policy_version",
        "confidence_threshold",
        "stages",
        "owner",
        "router_access",
    }
    missing = sorted(required - set(data))
    if missing:
        fail(f"missing keys {missing}")
    if data["schema_version"] != 1:
        fail(f"unsupported schema_version {data['schema_version']!r}")
    if not isinstance(data["policy_version"], int) or data["policy_version"] < 1:
        fail("policy_version must be a positive integer")
    threshold = data["confidence_threshold"]
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
        fail("confidence_threshold must be a number")
    if not 0.0 < float(threshold) <= 1.0:
        fail(f"confidence_threshold {threshold!r} must be in (0, 1]")
    stages = data["stages"]
    if not isinstance(stages, list) or not stages:
        fail("stages must be a non-empty list")
    unknown = [s for s in stages if s not in OFFICIAL_STAGES]
    if unknown:
        fail(f"stages contains values outside the official cascade: {unknown}")
    if len(set(stages)) != len(stages):
        fail("stages contains duplicates")
    ranks = [OFFICIAL_STAGES.index(s) for s in stages]
    if ranks != sorted(ranks):
        fail("stages must keep the official cascade order")
    if data["owner"] != "evolution_engine":
        fail(f"owner must be 'evolution_engine', got {data['owner']!r}")
    if data["router_access"] != "read_only":
        fail(f"router_access must be 'read_only', got {data['router_access']!r}")


def load_policy(path: str | os.PathLike[str] | None = None) -> RoutingPolicy:
    """Read the versioned policy file. Never writes, never creates."""
    resolved = resolve_policy_path(path)
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PolicyError(f"invalid routing policy at {resolved}: {exc}") from exc
    if not isinstance(data, dict):
        raise PolicyError(f"invalid routing policy at {resolved}: expected an object")
    _validate(data, resolved)
    return RoutingPolicy(
        version=int(data["policy_version"]),
        confidence_threshold=float(data["confidence_threshold"]),
        stages=tuple(data["stages"]),
        owner=data["owner"],
        router_access=data["router_access"],
        schema_version=int(data["schema_version"]),
        source_path=str(resolved),
    )
