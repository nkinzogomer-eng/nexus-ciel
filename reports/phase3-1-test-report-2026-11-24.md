# Rapport de tests Phase 3.1 — 2026-11-24

## Commandes

- `/tmp/ciel-phase2-venv/bin/python -m compileall -q nexus tests scripts` — succès.
- `/tmp/ciel-phase2-venv/bin/python -m pytest -ra` — **100 passed, 2 skipped**.
- `git diff --check` — succès après correction du whitespace.
- Trois démonstrations `PYTHONPATH=. ... scripts/phase31_demo_*.py` — succès ; rapports JSON générés.

## Skips justifiés

1. `tests/test_phase2_postgres.py` : `NEXUS_DATABASE_URL` absent.
2. `tests/test_phase2_sigkill_gate.py` : `NEXUS_DATABASE_URL` absent.

Ces skips sont des limites d’environnement local, pas une validation PostgreSQL. Le CAS multi-instance PostgreSQL reste un bloqueur documenté et doit être vérifié en CI PostgreSQL/Compose.

## Couverture ajoutée

La suite Phase 3.1 couvre le premier échec d’un plan à trois étapes, la conservation des deux restantes, la correction puis reprise, l’échec intermédiaire, la conservation des étapes vérifiées, la réécriture des dépendances, l’échec de correction, l’absence de budget, la restauration après révision, l’incertitude sans replay, les résultats partiels, les coûts séparés et le journal des blocages.
