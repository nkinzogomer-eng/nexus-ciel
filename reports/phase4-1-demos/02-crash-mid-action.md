# Démonstration 2 — interruption brutale

**Objectif :** Tuer le processus au milieu du handler et restaurer sans rejeu.

## Environnement et état initial
{
  "python": "3.12.3",
  "branch": "hardening/ciel-phase4-1-reliability-recovery"
}

## Étapes et événements

1. Démarrer un processus enfant
1. SIGKILL après le premier appel handler
1. Restaurer le snapshot et bloquer le replay

## Résultats

```json
{
  "actions": [
    {
      "action_id": "12555eea-c873-5e33-8ed5-cfca98e5fa84",
      "actual_cost_usd": 0.0,
      "error": "restored from running state; automatic replay disabled",
      "idempotent_replay": true,
      "observation": {},
      "outcome": "uncertain",
      "status": "interrupted_uncertain"
    }
  ],
  "checks": {
    "journal_valid": true,
    "no_second_call": true,
    "restored_status": "interrupted_uncertain",
    "sigkill": true
  },
  "environment": {
    "branch": "hardening/ciel-phase4-1-reliability-recovery",
    "python": "3.12.3"
  },
  "handler_calls": 1,
  "journal_events": [
    "action_requested",
    "action_authorized",
    "action_started",
    "action_recovery_blocked"
  ],
  "limitations": [
    "single-writer PostgreSQL",
    "no process sandbox",
    "handler timeout is observed after return and is not interruptible"
  ],
  "objective": "Tuer le processus au milieu du handler et restaurer sans rejeu.",
  "steps": [
    "D\u00e9marrer un processus enfant",
    "SIGKILL apr\u00e8s le premier appel handler",
    "Restaurer le snapshot et bloquer le replay"
  ],
  "title": "D\u00e9monstration 2 \u2014 interruption brutale"
}
```

## Limites

- single-writer PostgreSQL
- no process sandbox
- handler timeout is observed after return and is not interruptible
