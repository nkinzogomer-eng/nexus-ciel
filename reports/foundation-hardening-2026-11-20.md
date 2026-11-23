# Rapport de stabilisation technique et préparation cognitive

## Périmètre et préservation

La branche `hardening/ciel-foundation-2026-11-20` est créée depuis la meilleure
base candidate vérifiée : PR #10 HEAD `322bfd3b1e8a0697e1d7c866ffbca2696f716c35`,
dont la CI `42051032012` est verte avec 71 tests, PostgreSQL et Compose.

`main` (`3d8cf71`), PR #10 et Memory Core (`d2aa828`) ne sont pas modifiés. Aucun
merge, rebase destructif, reset, force push ou suppression n’est autorisé.
Aetherion et PRISM ne sont pas intégrés.

## Correction effectuée

Le test `test_postgres_store_restores_runtime_after_restart` accédait à
`os.environ["NEXUS_DATABASE_URL"]` sans garde. Hors CI, il échouait par `KeyError`
au lieu d’indiquer le prérequis manquant.

Correction limitée : le test d’intégration PostgreSQL est maintenant marqué
`skip` lorsque `NEXUS_DATABASE_URL` est absent. Le test de normalisation DSN
reste exécutable sans PostgreSQL. Le skip ne transforme pas un test DB en succès
et la CI conserve son service PostgreSQL obligatoire.

## Problèmes restants

- La persistance est un snapshot JSON unique, pas encore un ledger d’étapes.
- La récupération après crash abandonne ; elle ne rejoue pas de manière sûre.
- Les limites deadline, tokens, itérations et temps ne couvrent pas encore toutes
  les actions futures.
- Aucun planner multiétapes, executor d’outils, observation engine ou stratégie
  corrective n’est implémenté.
- Memory Core est in-memory et non intégré.
- Les documents de `main` comportent des références historiques obsolètes.
- Les retries et circuit breakers ne sont pas disponibles.

## Résultats attendus après correction

Commande sans base :

```bash
python -m pytest -q
```

Résultat attendu hors environnement DB : tests fonctionnels passés, test de
restauration PostgreSQL explicitement `skipped`, sans `KeyError`.

Résultat effectivement obtenu sur cette branche sans service PostgreSQL :
**69 passed, 2 skipped in 0.26s**. Les skips sont explicitement motivés par
l’absence de `NEXUS_DATABASE_URL`.

Commande avec base :

```bash
NEXUS_DATABASE_URL=postgresql://nexus:nexus@localhost:5432/nexus_ciel \
  alembic upgrade head
NEXUS_DATABASE_URL=postgresql://nexus:nexus@localhost:5432/nexus_ciel \
  python -m pytest -q tests/test_phase2_postgres.py tests/test_phase2_sigkill_gate.py
```

La gate SIGKILL exige en plus un PostgreSQL joignable et le schéma migré.

## Architecture livrée

L’architecture cible et les contrats sont dans :

- `docs/cognitive-engine-architecture.md` ;
- `docs/cognitive-contracts.md` ;
- `docs/capability-matrix.md`.

Ils définissent Goal/Mission, Planner, Plan/Step, Strategy, Executor, Tool
Registry, Observation, Verification, Memory, Ledger, Recovery, Budget, Policy
et Diagnostics. Ils ne déclarent aucune nouvelle capacité implémentée.

## Foundation-Ready

**Foundation-Ready dans le périmètre actuel :** contrats de mission, routeur
borné, garde budgétaire monétaire, vérification de sortie limitée, journal
chaîné, persistance snapshot et abandon contrôlé après crash — sur PR #10 avec
preuves CI correspondantes.

**Pas Foundation-Ready :** autonomie cognitive, planning multiétapes, outils,
observation d’effets, correction de stratégie, reprise sans duplication,
mémoire durable, SkillCards intégrées et interface d’approbation.

## Plan d’implémentation

1. Reproductibilité : correction DB, installation propre, CI et documentation.
2. Contrats persistants Plan/Step/Action/Observation/Effect.
3. Policy/Safety et Tool Registry en environnement sandbox contrôlé.
4. Executor + Verification avec pré/postconditions et idempotence.
5. Recovery par étape ; abandon si effet inconnu.
6. Memory Core PostgreSQL, provenance et contradictions.
7. Scénarios held-out sans LLM puis avec LLM facultatif.

Chaque étape doit être une branche isolée, un commit traçable, des tests
reproductibles et une CI verte avant la suivante.

## Coûts, risques et ressources

- Stabilisation : faible coût, 0,5–1 jour d’ingénierie ; risque faible.
- Contrats Plan/Step/Ledger : 2–4 jours ; risque moyen de migration.
- Sandbox et permissions outils : 4–8 jours ; risque élevé de sécurité.
- Recovery idempotent : 3–6 jours ; risque élevé de double effet.
- Memory Core durable : 3–6 jours ; risque moyen de provenance et fuite.
- Scénarios et mesure : 2–4 jours ; nécessite PostgreSQL, Docker et outils
  simulés déterministes.

Ressources minimales : un mainteneur Python/Pydantic/SQL, revue sécurité pour
les outils, PostgreSQL de CI, Docker de CI et une suite de scénarios contrôlés.
Aucun fournisseur LLM payant n’est requis pour les premières étapes.

## Décision

Ne pas implémenter le moteur cognitif dans cette intervention. Valider d’abord
la correction de reproductibilité puis soumettre l’architecture et les
contrats à revue. Conserver les branches existantes intactes.
