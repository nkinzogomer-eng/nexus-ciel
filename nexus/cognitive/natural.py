from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from .models import GoalUnderstanding, Hypothesis


NaturalStatus = Literal["accepted", "needs_clarification"]


class GoalInputAnalysis(BaseModel):
    """Bounded, auditable interpretation; it is not a general language model."""

    source_text: str = Field(min_length=1, max_length=2000)
    status: NaturalStatus
    objective: str = Field(min_length=1)
    expected_results: list[str] = Field(min_length=1)
    explicit_constraints: dict[str, Any] = Field(default_factory=dict)
    implicit_constraints: list[str] = Field(default_factory=list)
    known_facts: dict[str, Any] = Field(default_factory=dict)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(min_length=1)
    approval_required_tools: list[str] = Field(default_factory=list)
    blocking_questions: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

    @property
    def is_blocked(self) -> bool:
        return self.status == "needs_clarification"

    def to_goal(self) -> GoalUnderstanding:
        constraints = dict(self.explicit_constraints)
        constraints["implicit_constraints"] = list(self.implicit_constraints)
        constraints["risks"] = list(self.risks)
        constraints["approval_required_tools"] = list(self.approval_required_tools)
        if self.blocking_questions:
            constraints["required_information"] = [
                {"name": item, "classification": "blocking", "reason": "natural-language ambiguity"}
                for item in self.blocking_questions
            ]
        return GoalUnderstanding(
            objective=self.objective,
            expected_results=list(self.expected_results),
            constraints=constraints,
            success_criteria=list(self.success_criteria),
            limits=[*self.implicit_constraints],
            known_facts=dict(self.known_facts),
            unknowns=list(self.unknowns),
            hypotheses=list(self.hypotheses),
            confidence=self.confidence,
        )


class NaturalGoalInterpreter:
    """Parse only explicit, small patterns and abstain on unsafe ambiguity."""

    _budget = re.compile(r"\bbudget(?:\s+us[d$]|\s+de)?\s*[:=]?\s*(\d+(?:[\.,]\d+)?)", re.I)
    _fact = re.compile(r"(?:sachant\s+que|known\s+fact)\s+([\w.-]+)\s*=\s*([^,;.]+)", re.I)
    _hypothesis = re.compile(r"(?:supposons\s+que|assuming)\s+([^,.;]+)", re.I)
    _unknown = re.compile(r"(?:il\s+manque|information\s+manquante|unknown)\s*[:]?\s*([^,.;]+)", re.I)
    _verify = re.compile(r"(?:v[ée]rifie(?:r)?\s+que|verify(?:\s+that)?)\s+([^,.;]+)", re.I)
    _expected_result = re.compile(r"(?:r[ée]sultat|result)\s+(?:vaut|is|equals?)\s+(-?\d+(?:[\.,]\d+)?)", re.I)
    _duration = re.compile(r"\b(?:dur[ée]e|max(?:imum)?|within)\s*[:=]?\s*(\d+(?:[\.,]\d+)?)\s*(s|sec|secondes?|min|minutes?)", re.I)

    def interpret(self, text: str) -> GoalInputAnalysis:
        source = text.strip()
        if not source:
            raise ValueError("natural goal must not be blank")
        if len(source) > 2000:
            raise ValueError("natural goal exceeds 2000 characters")

        known: dict[str, Any] = {}
        for match in self._fact.finditer(source):
            known[match.group(1)] = self._scalar(match.group(2).strip())
        hypotheses = [Hypothesis(statement=item.group(1).strip(), confidence=0.5, basis=["explicit conditional wording"])
                      for item in self._hypothesis.finditer(source)]
        unknowns = [item.group(1).strip() for item in self._unknown.finditer(source)]
        budget_match = self._budget.search(source)
        explicit: dict[str, Any] = {}
        if budget_match:
            explicit["budget_usd"] = float(budget_match.group(1).replace(",", "."))
        duration_match = self._duration.search(source)
        if duration_match:
            unit = duration_match.group(2).lower()
            value = float(duration_match.group(1).replace(",", "."))
            explicit["max_duration_s"] = value * (60.0 if unit.startswith("min") else 1.0)

        verification = [item.group(1).strip() for item in self._verify.finditer(source)]
        expected_result = self._expected_result.search(source)
        if expected_result:
            explicit["expected_observations"] = {
                "result": self._scalar(expected_result.group(1).replace(",", "."))
            }
        objective = self._objective(source)
        expected = self._expected(source, objective)
        approvals: list[str] = []
        risks: list[str] = []
        ambiguities: list[str] = []
        blocking: list[str] = []
        lowered = source.lower()
        if re.search(r"\b(?:écri|ecri|modifi|supprim|write|delete|remove)", lowered):
            approvals.append("write_workspace")
            risks.append("workspace mutation requires explicit permission and persistent approval")
            if not re.search(r"(?:fichier|file|chemin|path)\s*[=:]?\s*[\w./_-]+", lowered):
                blocking.append("workspace target path")
                ambiguities.append("a workspace mutation is requested without an explicit target path")
        if re.search(r"\b(?:à la fois|both)\b", lowered) and re.search(r"\b(?:sans|without)\b", lowered):
            ambiguities.append("the request combines potentially incompatible positive and negative requirements")
            blocking.append("resolve contradictory requirements")
        if "contradiction:" in lowered or "contradiction " in lowered:
            contradictions = ["explicit contradiction marker in request"]
            blocking.append("contradictory requirement")
        else:
            contradictions = []

        if not verification:
            verification = ["the requested result is produced and observed"]
            risks.append("no independent machine-checkable oracle was supplied")
        implicit = [
            "do not use unallowlisted tools",
            "do not exceed declared budgets or limits",
            "do not replay uncertain effects automatically",
        ]
        if not budget_match:
            risks.append("budget was not stated; the runtime default remains in force")
        decisions = ["continue without clarification for non-blocking unknowns"]
        decisions.extend(f"require approval before {tool}" for tool in approvals)
        status: NaturalStatus = "needs_clarification" if blocking else "accepted"
        confidence = 0.55 if status == "accepted" else 0.25
        return GoalInputAnalysis(
            source_text=source,
            status=status,
            objective=objective,
            expected_results=expected,
            explicit_constraints=explicit,
            implicit_constraints=implicit,
            known_facts=known,
            hypotheses=hypotheses,
            unknowns=unknowns,
            ambiguities=ambiguities,
            contradictions=contradictions,
            risks=risks,
            decisions=decisions,
            success_criteria=verification,
            approval_required_tools=approvals,
            blocking_questions=list(dict.fromkeys(blocking)),
            confidence=confidence,
        )

    @staticmethod
    def _objective(source: str) -> str:
        objective = re.split(r"\b(?:avec|with|sachant que|known fact|v[ée]rifie|verify|budget)\b", source, maxsplit=1, flags=re.I)[0].strip(" ,;:")
        return objective or source

    @staticmethod
    def _expected(source: str, objective: str) -> list[str]:
        match = re.search(r"(?:r[ée]sultat|result)\s*[:=]?\s*([^.;]+)", source, re.I)
        return [match.group(1).strip()] if match else [objective]

    @staticmethod
    def _scalar(value: str) -> Any:
        if re.fullmatch(r"-?\d+", value):
            return int(value)
        if re.fullmatch(r"-?\d+[\.,]\d+", value):
            return float(value.replace(",", "."))
        return value
