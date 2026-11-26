# Démonstration 3 — restauration sans rejeu

**Objectif :** Restaurer un running et prouver le blocage sans appel handler.

## Environnement et état initial
{
  "python": "3.12.3",
  "branch": "hardening/ciel-phase4-1-reliability-recovery"
}

## Étapes et événements

1. Restaurer un record running
1. Demander la même action
1. Contrôler interrupted_uncertain et le journal

## Résultats

```json
{
  "actions": [
    {
      "action_id": "a008e14c-fd62-529e-9777-1ed6fef2173a",
      "actual_cost_usd": 0.0,
      "error": "restored from running state; automatic replay disabled",
      "idempotent_replay": true,
      "observation": {},
      "outcome": "uncertain",
      "status": "interrupted_uncertain"
    }
  ],
  "checks": {
    "blocked": true,
    "journal_valid": true,
    "no_replay": true
  },
  "environment": {
    "branch": "hardening/ciel-phase4-1-reliability-recovery",
    "python": "3.12.3"
  },
  "handler_calls": 0,
  "journal_events": [
    "action_recovery_blocked"
  ],
  "limitations": [
    "single-writer PostgreSQL",
    "no process sandbox",
    "handler timeout is observed after return and is not interruptible"
  ],
  "objective": "Restaurer un running et prouver le blocage sans appel handler.",
  "steps": [
    "Restaurer un record running",
    "Demander la m\u00eame action",
    "Contr\u00f4ler interrupted_uncertain et le journal"
  ],
  "title": "D\u00e9monstration 3 \u2014 restauration sans rejeu"
}
```

## Limites

- single-writer PostgreSQL
- no process sandbox
- handler timeout is observed after return and is not interruptible
