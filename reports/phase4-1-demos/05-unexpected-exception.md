# Démonstration 5 — exception inattendue

**Objectif :** Classer une exception inconnue après démarrage comme résultat incertain terminal.

## Environnement et état initial
{
  "python": "3.12.3",
  "branch": "hardening/ciel-phase4-1-reliability-recovery"
}

## Étapes et événements

1. Lancer un handler qui lève KeyError
1. Contrôler interrupted_uncertain
1. Rejouer et vérifier zéro nouvel appel

## Résultats

```json
{
  "actions": [
    {
      "action_id": "707025b3-441f-4c14-acba-1dfaa097f28a",
      "actual_cost_usd": 0.0,
      "error": "unexpected exception after handler start: KeyError: 'unexpected demo exception'",
      "idempotent_replay": false,
      "observation": {},
      "outcome": "uncertain",
      "status": "interrupted_uncertain"
    },
    {
      "action_id": "707025b3-441f-4c14-acba-1dfaa097f28a",
      "actual_cost_usd": 0.0,
      "error": "unexpected exception after handler start: KeyError: 'unexpected demo exception'",
      "idempotent_replay": true,
      "observation": {},
      "outcome": "uncertain",
      "status": "interrupted_uncertain"
    }
  ],
  "checks": {
    "no_replay": true,
    "uncertain": true
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
  "objective": "Classer une exception inconnue apr\u00e8s d\u00e9marrage comme r\u00e9sultat incertain terminal.",
  "steps": [
    "Lancer un handler qui l\u00e8ve KeyError",
    "Contr\u00f4ler interrupted_uncertain",
    "Rejouer et v\u00e9rifier z\u00e9ro nouvel appel"
  ],
  "title": "D\u00e9monstration 5 \u2014 exception inattendue"
}
```

## Limites

- single-writer PostgreSQL
- no process sandbox
- handler timeout is observed after return and is not interruptible
