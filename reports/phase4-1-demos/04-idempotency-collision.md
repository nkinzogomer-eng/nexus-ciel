# Démonstration 4 — collision d’idempotence

**Objectif :** Refuser une même clé liée à un budget différent.

## Environnement et état initial
{
  "python": "3.12.3",
  "branch": "hardening/ciel-phase4-1-reliability-recovery"
}

## Étapes et événements

1. Exécuter la requête originale
1. Soumettre la même clé avec un budget différent
1. Vérifier le refus et l’unicité d’exécution

## Résultats

```json
{
  "actions": [
    {
      "action_id": "7e6a8fb3-3e64-4dc0-b0cb-3be4d3d1587e",
      "actual_cost_usd": 0.0,
      "error": null,
      "idempotent_replay": false,
      "observation": {
        "ok": true,
        "value": 1
      },
      "outcome": "success",
      "status": "succeeded"
    }
  ],
  "checks": {
    "collision_rejected": true,
    "error": "idempotency key is bound to a different action identity",
    "one_handler_call": true
  },
  "environment": {
    "branch": "hardening/ciel-phase4-1-reliability-recovery",
    "python": "3.12.3"
  },
  "handler_calls": 1,
  "journal_events": [],
  "limitations": [
    "single-writer PostgreSQL",
    "no process sandbox",
    "handler timeout is observed after return and is not interruptible"
  ],
  "objective": "Refuser une m\u00eame cl\u00e9 li\u00e9e \u00e0 un budget diff\u00e9rent.",
  "steps": [
    "Ex\u00e9cuter la requ\u00eate originale",
    "Soumettre la m\u00eame cl\u00e9 avec un budget diff\u00e9rent",
    "V\u00e9rifier le refus et l\u2019unicit\u00e9 d\u2019ex\u00e9cution"
  ],
  "title": "D\u00e9monstration 4 \u2014 collision d\u2019idempotence"
}
```

## Limites

- single-writer PostgreSQL
- no process sandbox
- handler timeout is observed after return and is not interruptible
