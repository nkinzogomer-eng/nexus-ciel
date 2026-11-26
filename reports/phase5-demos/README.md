# Démonstrations Phase 5

Les trois parcours utilisent les composants CIEL réels. Le troisième tue réellement un processus enfant par SIGKILL ; la politique de recovery constate l’incertitude et interdit le rejeu automatique.

## nominal

```json
{
  "action": {
    "action_id": "10a9b784-f9c2-47ac-91e0-c860c5be29df",
    "actual_cost_usd": 0.01,
    "error": null,
    "idempotent_replay": false,
    "observation": {
      "count": 2,
      "ok": true,
      "operation": "add",
      "result": 10
    },
    "outcome": "success",
    "status": "succeeded"
  },
  "final_status": "succeeded",
  "input": {
    "ambiguities": [],
    "approval_required_tools": [],
    "blocking_questions": [],
    "confidence": 0.55,
    "contradictions": [],
    "decisions": [
      "continue without clarification for non-blocking unknowns"
    ],
    "expected_results": [
      "vaut 10"
    ],
    "explicit_constraints": {
      "budget_usd": 1.0,
      "expected_observations": {
        "result": 10
      }
    },
    "hypotheses": [],
    "implicit_constraints": [
      "do not use unallowlisted tools",
      "do not exceed declared budgets or limits",
      "do not replay uncertain effects automatically"
    ],
    "known_facts": {},
    "objective": "Calcule la somme 4 et 6",
    "risks": [],
    "source_text": "Calcule la somme 4 et 6, avec budget 1, v\u00e9rifie que le r\u00e9sultat vaut 10",
    "status": "accepted",
    "success_criteria": [
      "le r\u00e9sultat vaut 10"
    ],
    "unknowns": []
  },
  "mission": "nominal",
  "strategy": {
    "candidate_name": "staged-verified",
    "deterministic_key": "staged-verified:1.2:0.75|direct-bounded:1.0:0.5|cost-minimal-checkpointed:0.85:0.25",
    "reasons": [
      "highest deterministic adjusted score (1.140)",
      "estimated cost 0.75 <= budget 1.0",
      "stronger verification",
      "lower uncertainty"
    ],
    "rejected_candidates": [
      "d9ad1e23-e855-5740-81c9-587264a86db0",
      "4d7d892d-f2b7-5fe1-9a06-aa901f3720fa"
    ],
    "selected_at": "2026-11-26T04:59:27.266927Z",
    "strategy_id": "b950081c-c8a8-5e0d-b51c-7fc32d8286ee"
  }
}
```

## failure_and_adaptation

```json
{
  "corrected_action": {
    "action_id": "daa9866b-7843-4998-8fba-9713a1732c52",
    "actual_cost_usd": 0.01,
    "error": null,
    "idempotent_replay": false,
    "observation": {
      "count": 2,
      "ok": true,
      "operation": "add",
      "result": 5
    },
    "outcome": "success",
    "status": "succeeded"
  },
  "failed_action": {
    "action_id": "5eb50898-969a-463f-b66b-4f1c885cbc8c",
    "actual_cost_usd": 0.0,
    "error": "controlled demo failure",
    "idempotent_replay": false,
    "observation": {},
    "outcome": "failure",
    "status": "failed"
  },
  "final_status": "succeeded",
  "input": {
    "ambiguities": [],
    "approval_required_tools": [],
    "blocking_questions": [],
    "confidence": 0.55,
    "contradictions": [],
    "decisions": [
      "continue without clarification for non-blocking unknowns"
    ],
    "expected_results": [
      "Calcule une valeur de correction"
    ],
    "explicit_constraints": {
      "budget_usd": 1.0
    },
    "hypotheses": [],
    "implicit_constraints": [
      "do not use unallowlisted tools",
      "do not exceed declared budgets or limits",
      "do not replay uncertain effects automatically"
    ],
    "known_facts": {},
    "objective": "Calcule une valeur de correction",
    "risks": [
      "no independent machine-checkable oracle was supplied"
    ],
    "source_text": "Calcule une valeur de correction avec budget 1",
    "status": "accepted",
    "success_criteria": [
      "the requested result is produced and observed"
    ],
    "unknowns": []
  },
  "mission": "failure_and_adaptation",
  "revision": {
    "candidates": [
      {
        "advantages": [
          "shortest deterministic path"
        ],
        "constraint_violations": [],
        "dependencies": {
          "Calcule une valeur de correction": []
        },
        "estimated_cost_usd": 0.5,
        "estimated_duration_s": 60.0,
        "limits": [
          "requires complete observations"
        ],
        "name": "direct-bounded",
        "objective": "Calcule une valeur de correction",
        "planned_steps": [
          "Calcule une valeur de correction"
        ],
        "preconditions": [],
        "required_information": [],
        "reversible": true,
        "risk_level": 0.5,
        "risks": [
          "limited correction path"
        ],
        "score": 1.0,
        "score_justification": [
          "fewer steps",
          "higher declared correction risk"
        ],
        "strategy_id": "f8d23441-dffd-5e06-b812-109d473c109c",
        "success_criteria": [
          "the requested result is produced and observed"
        ],
        "uncertainty": 0.3
      },
      {
        "advantages": [
          "explicit verification boundary",
          "safer correction point"
        ],
        "constraint_violations": [],
        "dependencies": {
          "Calcule une valeur de correction": []
        },
        "estimated_cost_usd": 0.75,
        "estimated_duration_s": 90.0,
        "limits": [
          "requires an observation per stage"
        ],
        "name": "staged-verified",
        "objective": "Calcule une valeur de correction",
        "planned_steps": [
          "verify:Calcule une valeur de correction"
        ],
        "preconditions": [],
        "required_information": [],
        "reversible": true,
        "risk_level": 0.2,
        "risks": [
          "higher declared cost"
        ],
        "score": 1.2,
        "score_justification": [
          "stronger verification",
          "lower uncertainty"
        ],
        "strategy_id": "f5e2d39a-4989-5397-a2dc-41902b6701d9",
        "success_criteria": [
          "the requested result is produced and observed"
        ],
        "uncertainty": 0.1
      },
      {
        "advantages": [
          "lowest declared cost",
          "reversible checkpoints"
        ],
        "constraint_violations": [],
        "dependencies": {
          "Calcule une valeur de correction": []
        },
        "estimated_cost_usd": 0.25,
        "estimated_duration_s": 120.0,
        "limits": [
          "not suitable for urgent deadlines"
        ],
        "name": "cost-minimal-checkpointed",
        "objective": "Calcule une valeur de correction",
        "planned_steps": [
          "checkpoint:Calcule une valeur de correction"
        ],
        "preconditions": [],
        "required_information": [],
        "reversible": true,
        "risk_level": 0.7,
        "risks": [
          "slower progress",
          "higher uncertainty"
        ],
        "score": 0.85,
        "score_justification": [
          "lowest cost",
          "penalized for risk and duration"
        ],
        "strategy_id": "89836815-b7ca-549c-8148-49a05707e981",
        "success_criteria": [
          "the requested result is produced and observed"
        ],
        "uncertainty": 0.5
      }
    ],
    "created_at": "2026-11-26T04:59:27.267808Z",
    "cycle_id": "0eb07763-d776-439f-9d36-5534d9614033",
    "decisions": [
      {
        "authority": "deterministic_core",
        "created_at": "2026-11-26T04:59:27.267710Z",
        "decision_id": "9f4d0a50-ca33-412d-8039-3cb31965950f",
        "evidence": [
          "deterministic candidate comparison"
        ],
        "kind": "select_strategy",
        "llm_advice_digest": null,
        "reasons": [
          "highest deterministic adjusted score (1.140)",
          "estimated cost 0.75 <= budget 1.0",
          "stronger verification",
          "lower uncertainty"
        ],
        "subject_id": "f5e2d39a-4989-5397-a2dc-41902b6701d9"
      },
      {
        "authority": "deterministic_core",
        "created_at": "2026-11-26T04:59:27.267965Z",
        "decision_id": "6727fbc3-126b-49cc-b001-233ca9581215",
        "evidence": [
          "failed observation"
        ],
        "kind": "revise",
        "llm_advice_digest": null,
        "reasons": [
          "failure was observed; use a deterministic correction"
        ],
        "subject_id": "0f9179de-f4fb-4e8d-873b-9ca1c8a1bfce"
      }
    ],
    "goal": {
      "confidence": 0.55,
      "constraints": {
        "approval_required_tools": [],
        "budget_usd": 1.0,
        "implicit_constraints": [
          "do not use unallowlisted tools",
          "do not exceed declared budgets or limits",
          "do not replay uncertain effects automatically"
        ],
        "risks": [
          "no independent machine-checkable oracle was supplied"
        ]
      },
      "expected_results": [
        "Calcule une valeur de correction"
      ],
      "hypotheses": [],
      "known_facts": {},
      "limits": [
        "do not use unallowlisted tools",
        "do not exceed declared budgets or limits",
        "do not replay uncertain effects automatically"
      ],
      "objective": "Calcule une valeur de correction",
      "success_criteria": [
        "the requested result is produced and observed"
      ],
      "unknowns": []
    },
    "mission": {
      "assumptions": [],
      "confidence": 0.55,
      "constraints": {
        "approval_required_tools": [],
        "budget_usd": 1.0,
        "implicit_constraints": [
          "do not use unallowlisted tools",
          "do not exceed declared budgets or limits",
          "do not replay uncertain effects automatically"
        ],
        "risks": [
          "no independent machine-checkable oracle was supplied"
        ]
      },
      "dependencies": {
        "Calcule une valeur de correction": []
      },
      "expected_results": [
        "Calcule une valeur de correction"
      ],
      "missing_information": [],
      "missing_information_details": [],
      "mission_id": "b4d34bb7-fc9e-4120-a7ed-21905929eb95",
      "objective": "Calcule une valeur de correction",
      "subgoals": [
        "Calcule une valeur de correction"
      ],
      "success_criteria": [
        "the requested result is produced and observed"
      ]
    },
    "mode": "CORE_ONLY",
    "observations": [],
    "plan_id": "0f9179de-f4fb-4e8d-873b-9ca1c8a1bfce",
    "selection": {
      "candidate_name": "staged-verified",
      "deterministic_key": "staged-verified:1.2:0.75|direct-bounded:1.0:0.5|cost-minimal-checkpointed:0.85:0.25",
      "reasons": [
        "highest deterministic adjusted score (1.140)",
        "estimated cost 0.75 <= budget 1.0",
        "stronger verification",
        "lower uncertainty"
      ],
      "rejected_candidates": [
        "f8d23441-dffd-5e06-b812-109d473c109c",
        "89836815-b7ca-549c-8148-49a05707e981"
      ],
      "selected_at": "2026-11-26T04:59:27.267704Z",
      "strategy_id": "f5e2d39a-4989-5397-a2dc-41902b6701d9"
    },
    "status": "running",
    "updated_at": "2026-11-26T04:59:27.267967Z"
  }
}
```

## real_interruption

```json
{
  "automatic_replay": false,
  "expected_signal": -9,
  "handler_calls": [
    "handler"
  ],
  "mission": "real_interruption",
  "process_return_code": -9,
  "replay_status": "interrupted_uncertain",
  "replay_was_idempotent": true,
  "restored_status": "interrupted_uncertain"
}
```
