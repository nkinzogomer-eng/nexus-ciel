# Phase 4 demonstration — security-refusal

```json
{
  "costs": {
    "consumed": 0.0
  },
  "decisions": [
    {
      "kind": "REJECT",
      "reason": "tool is not registered or unavailable: shell"
    }
  ],
  "final_state": "rejected",
  "limits": [
    "No shell, network, browser or arbitrary filesystem tool is registered."
  ],
  "objective": "refuse an unregistered arbitrary command",
  "observations": [
    {
      "action_id": "36213ea7-7633-4334-8e9b-042de39d145e",
      "actual_cost_usd": 0.0,
      "error": "tool is not registered or unavailable: shell",
      "idempotent_replay": false,
      "observation": {},
      "outcome": "failure",
      "status": "rejected"
    }
  ],
  "permissions": [
    "shell"
  ],
  "steps": [],
  "tools_called": [],
  "verifications": {
    "no_effect": true,
    "unregistered_refused": true
  }
}
```
