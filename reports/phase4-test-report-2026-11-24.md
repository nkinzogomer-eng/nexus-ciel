# Rapport de tests Phase 4 MVP — 2026-11-24

La compilation `python -m compileall -q nexus tests scripts` est réussie. La suite complète locale est à **110 passed, 2 skipped**. Les deux skips concernent les tests PostgreSQL/SIGKILL conditionnés par l’absence de `NEXUS_DATABASE_URL` ; ils ne sont pas présentés comme une preuve PostgreSQL locale.

Les tests ajoutés couvrent le calcul déterministe réel, l’outil non enregistré, les permissions manquantes, l’approbation obligatoire d’écriture, la validation de paramètres et de budget, la protection contre la traversée de workspace, l’idempotence, les résultats incertains, l’intégration Cognitive Engine → Action Executor → Observation → Vérification et la restauration persistante des actions.

Les cinq démonstrations ont été exécutées par `scripts/phase4_demo_suite.py`. Les rapports JSON et Markdown correspondants sont `phase4-demo-nominal`, `phase4-demo-error-correction`, `phase4-demo-interruption-restore`, `phase4-demo-security-refusal` et `phase4-demo-core-only`.

La CI PostgreSQL/Compose de la PR #13 précédente était verte. La nouvelle branche devra être poussée et validée par sa propre CI avant toute conclusion de release.
