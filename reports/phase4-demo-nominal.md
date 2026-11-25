# Phase 4 demonstration — nominal

```json
{
  "costs": {
    "consumed": 0.02
  },
  "decisions": [
    {
      "authority": "deterministic_core",
      "created_at": "2026-11-25T08:16:15.113043Z",
      "decision_id": "efa0ae5f-e24b-407d-bb4e-aeab2e85ab49",
      "evidence": [
        "deterministic candidate comparison"
      ],
      "kind": "select_strategy",
      "llm_advice_digest": null,
      "reasons": [
        "highest deterministic adjusted score (1.140)",
        "estimated cost 1.5 <= budget 5.0",
        "stronger verification",
        "lower uncertainty"
      ],
      "subject_id": "f8e6b262-9e20-55ab-a68d-1576a3723d88"
    },
    {
      "authority": "deterministic_core",
      "created_at": "2026-11-25T08:16:15.113390Z",
      "decision_id": "2b8235b5-aaf6-48e8-aae6-42d951e23b75",
      "evidence": [
        "7fee8035-ee63-4e0a-8a13-5512fb694b2c"
      ],
      "kind": "keep",
      "llm_advice_digest": null,
      "reasons": [
        "postconditions verified"
      ],
      "subject_id": "f01ee820-544c-4ec5-9fa1-1aad9a7c5f36"
    },
    {
      "authority": "deterministic_core",
      "created_at": "2026-11-25T08:16:15.113743Z",
      "decision_id": "81ec3877-6e7b-4d9d-a663-ca7e9a1fe4b0",
      "evidence": [
        "fcf76fbf-91d6-465b-98d4-1f2c889692db"
      ],
      "kind": "keep",
      "llm_advice_digest": null,
      "reasons": [
        "postconditions verified"
      ],
      "subject_id": "f01ee820-544c-4ec5-9fa1-1aad9a7c5f36"
    }
  ],
  "final_state": "succeeded",
  "limits": [
    "Only deterministic registered tools are used."
  ],
  "objective": "compute two bounded results",
  "observations": [
    {
      "action_id": "27bb35bb-b579-4d69-83bd-e2018ca087f1",
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
    },
    {
      "action_id": "e7ba6c3c-686d-47cd-a025-422bead25bc9",
      "actual_cost_usd": 0.01,
      "error": null,
      "idempotent_replay": false,
      "observation": {
        "count": 2,
        "ok": true,
        "operation": "add",
        "result": 4
      },
      "outcome": "success",
      "status": "succeeded"
    }
  ],
  "permissions": [
    "compute"
  ],
  "steps": [
    {
      "action_ref": "tool:calculate",
      "budget_usd": 0.75,
      "depends_on": [],
      "error": null,
      "estimated_cost_usd": 0.01,
      "idempotency_key": "cognitive:cb61b8a4-0782-475b-870b-6d4a1831b5dc:f8e6b262-9e20-55ab-a68d-1576a3723d88:1",
      "justification": "declared by deterministic planner",
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
      "step_id": "04e4aea2-2222-4610-a5cf-cda0ed3049b6",
      "title": "verify:first"
    },
    {
      "action_ref": "tool:calculate",
      "budget_usd": 0.75,
      "depends_on": [
        "04e4aea2-2222-4610-a5cf-cda0ed3049b6"
      ],
      "error": null,
      "estimated_cost_usd": 0.01,
      "idempotency_key": "cognitive:cb61b8a4-0782-475b-870b-6d4a1831b5dc:f8e6b262-9e20-55ab-a68d-1576a3723d88:2",
      "justification": "declared by deterministic planner",
      "observation": {
        "count": 2,
        "ok": true,
        "operation": "add",
        "result": 4
      },
      "ordinal": 2,
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
      "step_id": "d700e641-1fa9-4f2b-a3ed-b58fdc389528",
      "title": "verify:second"
    }
  ],
  "tools_called": [
    "calculate",
    "calculate"
  ],
  "verifications": {
    "all_verified": true
  }
}
```
