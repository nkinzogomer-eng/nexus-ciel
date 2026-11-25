# Phase 4 demonstration — core-only

```json
{
  "costs": {
    "consumed": 0.01
  },
  "decisions": [
    {
      "authority": "deterministic_core",
      "created_at": "2026-11-25T08:16:15.119548Z",
      "decision_id": "a02a87bf-c142-406f-9a06-09b341f2c704",
      "evidence": [
        "deterministic candidate comparison"
      ],
      "kind": "select_strategy",
      "llm_advice_digest": null,
      "reasons": [
        "highest deterministic adjusted score (1.140)",
        "estimated cost 0.75 <= budget 2.0",
        "stronger verification",
        "lower uncertainty"
      ],
      "subject_id": "2a03e35a-0d7c-5db8-94ff-45e4d03ab938"
    },
    {
      "authority": "deterministic_core",
      "created_at": "2026-11-25T08:16:15.119759Z",
      "decision_id": "8f35af40-fe82-46c0-bad6-0036cbd70248",
      "evidence": [
        "7b753785-5720-4f76-bd56-42a9e6776076"
      ],
      "kind": "keep",
      "llm_advice_digest": null,
      "reasons": [
        "postconditions verified"
      ],
      "subject_id": "7fa11a4c-74cb-4406-882b-b0c07c2076b5"
    }
  ],
  "final_state": "succeeded",
  "limits": [
    "LLM providers are not involved."
  ],
  "objective": "run without an LLM",
  "observations": [
    {
      "action_id": "3f92a2ec-97de-495d-9530-67d376158d5b",
      "actual_cost_usd": 0.01,
      "error": null,
      "idempotent_replay": false,
      "observation": {
        "count": 2,
        "ok": true,
        "operation": "multiply",
        "result": 12
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
      "estimated_cost_usd": 0.0,
      "idempotency_key": "cognitive:144767c0-0551-427c-a63c-74e92b008109:2a03e35a-0d7c-5db8-94ff-45e4d03ab938:1",
      "justification": "declared by deterministic planner",
      "observation": null,
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
      "spent_cost_usd": 0.0,
      "status": "planned",
      "step_id": "2e2dd79d-fbde-4c01-bad3-aa60ca8da7c4",
      "title": "verify:calculation"
    }
  ],
  "tools_called": [
    "calculate"
  ],
  "verifications": {
    "all_verified": true,
    "core_only": true
  }
}
```
