# Phase 4 demonstration — error-correction

```json
{
  "costs": {
    "consumed": 0.01
  },
  "decisions": [
    {
      "authority": "deterministic_core",
      "created_at": "2026-11-25T08:16:15.114831Z",
      "decision_id": "7f134d60-602b-489f-9a78-a331fb192ccc",
      "evidence": [
        "deterministic candidate comparison"
      ],
      "kind": "select_strategy",
      "llm_advice_digest": null,
      "reasons": [
        "highest deterministic adjusted score (1.140)",
        "estimated cost 0.75 <= budget 5.0",
        "stronger verification",
        "lower uncertainty"
      ],
      "subject_id": "82f283b1-16c3-5e1c-b07e-63327fb7e278"
    },
    {
      "authority": "deterministic_core",
      "created_at": "2026-11-25T08:16:15.115054Z",
      "decision_id": "79fff92a-3bfa-4dd8-916d-d54b7574b3ae",
      "evidence": [
        "failed observation"
      ],
      "kind": "revise",
      "llm_advice_digest": null,
      "reasons": [
        "bounded correction required"
      ],
      "subject_id": "c12db737-3b74-4909-b503-a589533ebea9"
    },
    {
      "authority": "deterministic_core",
      "created_at": "2026-11-25T08:16:15.115284Z",
      "decision_id": "1b0afb3c-5b66-465b-b435-ff20bcc8f1ae",
      "evidence": [
        "b5bfb56a-184c-4c68-920a-0ee3a32ce3d5"
      ],
      "kind": "keep",
      "llm_advice_digest": null,
      "reasons": [
        "postconditions verified"
      ],
      "subject_id": "d6669bc6-e8c7-4756-ba16-31166a20443e"
    }
  ],
  "final_state": "succeeded",
  "limits": [
    "The remaining suffix still requires its own explicit execution and verification."
  ],
  "objective": "recover from a bounded failure",
  "observations": [
    {
      "action_id": "ad8a89ef-a4ac-4f9f-9a59-d14c191b97c9",
      "actual_cost_usd": 0.0,
      "error": "controlled demo failure",
      "idempotent_replay": false,
      "observation": {},
      "outcome": "failure",
      "status": "failed"
    },
    {
      "action_id": "eb157c1d-8258-451a-a6f2-ce349e8d270f",
      "actual_cost_usd": 0.01,
      "error": null,
      "idempotent_replay": false,
      "observation": {
        "count": 2,
        "ok": true,
        "operation": "add",
        "result": 2
      },
      "outcome": "success",
      "status": "succeeded"
    }
  ],
  "permissions": [
    "demo.simulate",
    "compute"
  ],
  "steps": [
    {
      "action_ref": "tool:calculate",
      "budget_usd": 5.0,
      "depends_on": [],
      "error": null,
      "estimated_cost_usd": 0.01,
      "idempotency_key": "correction:c12db737-3b74-4909-b503-a589533ebea9:1:cd4f0b46-30c4-4247-b1f8-2f5973ed2d8e",
      "justification": "bounded correction required",
      "observation": {
        "count": 2,
        "ok": true,
        "operation": "add",
        "result": 2
      },
      "ordinal": 1,
      "postconditions": [
        {
          "expected": true,
          "key": "ok",
          "operator": "equals"
        }
      ],
      "preconditions": [],
      "reserved_cost_usd": 0.0,
      "spent_cost_usd": 0.01,
      "status": "verified",
      "step_id": "f7bbcd71-e3fc-4dd0-ad13-459a0334d2a8",
      "title": "controlled-correction"
    }
  ],
  "tools_called": [
    "simulated_failure",
    "calculate"
  ],
  "verifications": {
    "failed_action_replayed": false,
    "suffix_or_correction_preserved": true
  }
}
```
