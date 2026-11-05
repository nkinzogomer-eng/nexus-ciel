from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from nexus.schemas import Mission


@dataclass(frozen=True)
class VerificationResult:
    verdict: str
    criteria: list[dict[str, Any]]
    evidence: dict[str, Any]


class DeterministicOutputVerifier:
    """Verify only explicit, machine-checkable acceptance contracts.

    A model confidence score is never treated as proof of task completion.
    Missing or unsupported oracles yield PARTIAL rather than a fabricated PASS.
    """

    SUPPORTED_MODES = {"contains_all", "contains_any", "exact_match", "json_valid", "non_empty"}

    def verify(self, mission: Mission, output: str | None) -> VerificationResult:
        spec = mission.constraints.get("verification")
        if not isinstance(spec, dict) or not spec:
            return VerificationResult(
                verdict="PARTIAL",
                criteria=[{
                    "name": "independent acceptance oracle supplied",
                    "passed": False,
                    "reason": "no deterministic verification contract was supplied",
                }],
                evidence={"oracle": None, "output_present": bool(output)},
            )

        mode = spec.get("mode")
        if mode not in self.SUPPORTED_MODES:
            return VerificationResult(
                verdict="PARTIAL",
                criteria=[{
                    "name": "supported deterministic verification mode",
                    "passed": False,
                    "reason": f"unsupported verification mode: {mode!r}",
                }],
                evidence={"oracle": spec, "output_present": bool(output)},
            )

        text = output or ""
        if mode == "non_empty":
            passed = bool(text.strip())
            detail = {"non_empty": passed}
        elif mode == "exact_match":
            expected = spec.get("expected")
            if not isinstance(expected, str):
                return VerificationResult(
                    verdict="PARTIAL",
                    criteria=[{"name": "valid exact_match oracle", "passed": False}],
                    evidence={"oracle": spec},
                )
            passed = text == expected
            detail = {"expected": expected, "actual": text, "matched": passed}
        elif mode == "json_valid":
            try:
                parsed = json.loads(text)
                passed = True
                detail = {"json_valid": True, "top_level_type": type(parsed).__name__}
            except (TypeError, ValueError):
                passed = False
                detail = {"json_valid": False}
        else:
            needles = spec.get("needles")
            if not isinstance(needles, list) or not needles or not all(isinstance(x, str) and x for x in needles):
                return VerificationResult(
                    verdict="PARTIAL",
                    criteria=[{"name": f"valid {mode} oracle", "passed": False}],
                    evidence={"oracle": spec},
                )
            matches = [needle for needle in needles if needle in text]
            passed = len(matches) == len(needles) if mode == "contains_all" else bool(matches)
            detail = {"required": needles, "matched": matches}

        return VerificationResult(
            verdict="PASS" if passed else "FAIL",
            criteria=[{"name": f"deterministic {mode} verification", "passed": passed}],
            evidence={"oracle": spec, "result": detail},
        )
