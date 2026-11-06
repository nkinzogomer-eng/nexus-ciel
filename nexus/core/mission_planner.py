from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class MissionPlanError(ValueError):
    """The declarative mission plan is malformed or unsafe to execute."""


@dataclass(frozen=True)
class PlannedStep:
    step_id: str
    kind: str
    task: str
    tool: str | None = None
    arguments: dict[str, Any] | None = None
    fallback_to: str | None = None
    depends_on: tuple[str, ...] = ()


class DeterministicMissionCompiler:
    """Compile an explicit, ordered plan; never ask a model to invent authority."""

    def compile(self, mission: Any) -> list[PlannedStep]:
        for scope_name in ("allowed_tools", "permissions"):
            scope = mission.constraints.get(scope_name, [])
            if not isinstance(scope, list) or any(not isinstance(item, str) or not item for item in scope):
                raise MissionPlanError(f"constraints.{scope_name} must be a list of non-empty strings")
            if len(set(scope)) != len(scope):
                raise MissionPlanError(f"constraints.{scope_name} must not contain duplicates")
        raw = mission.constraints.get("plan")
        if raw is None:
            # A single generation step is a deterministic, backwards-compatible plan.
            return [PlannedStep(step_id="mission", kind="generate", task=mission.objective)]
        if not isinstance(raw, list) or not raw:
            raise MissionPlanError("constraints.plan must be a non-empty list")

        by_id: dict[str, dict[str, Any]] = {}
        for item in raw:
            if not isinstance(item, dict):
                raise MissionPlanError("each plan step must be an object")
            step_id = item.get("id")
            if not isinstance(step_id, str) or not step_id or step_id in by_id:
                raise MissionPlanError("plan step ids must be unique non-empty strings")
            kind = item.get("kind")
            if kind not in {"generate", "tool"}:
                raise MissionPlanError(f"step {step_id!r} has unsupported kind")
            if kind == "tool" and not isinstance(item.get("tool"), str):
                raise MissionPlanError(f"tool step {step_id!r} requires a tool name")
            if kind == "generate" and not isinstance(item.get("task", mission.objective), str):
                raise MissionPlanError(f"generate step {step_id!r} requires a text task")
            by_id[step_id] = item

        # Preserve declared order and require dependencies to appear earlier.
        result: list[PlannedStep] = []
        seen: set[str] = set()
        for step_id, item in by_id.items():
            dependencies = item.get("depends_on", [])
            if not isinstance(dependencies, list) or any(dep not in seen for dep in dependencies):
                raise MissionPlanError(f"step {step_id!r} has a missing, forward, or cyclic dependency")
            fallback = item.get("fallback_to")
            if fallback is not None and (not isinstance(fallback, str) or fallback not in by_id):
                raise MissionPlanError(f"step {step_id!r} references an unknown fallback")
            args = item.get("arguments", {})
            if not isinstance(args, dict):
                raise MissionPlanError(f"step {step_id!r} arguments must be an object")
            result.append(PlannedStep(
                step_id=step_id,
                kind=item["kind"],
                task=item.get("task", mission.objective),
                tool=item.get("tool"),
                arguments=args,
                fallback_to=fallback,
                depends_on=tuple(dependencies),
            ))
            seen.add(step_id)
        positions = {step.step_id: index for index, step in enumerate(result)}
        for index, step in enumerate(result):
            if step.fallback_to is not None and positions[step.fallback_to] <= index:
                raise MissionPlanError("fallback targets must appear later in the plan")
        return result
