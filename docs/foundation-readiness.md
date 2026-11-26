# CIEL Foundation-Ready Decision

## Verdict

**Foundation-Ready partiel ; Plan/Step-ready et Cognitive-Engine initial-ready
dans les périmètres livrés ; pas Cognitive-Engine complet ni Tool-ready.**

La base PR #10 est suffisamment structurée pour continuer le durcissement de
la persistance, des contrats et de la sécurité. Elle n’est pas prête à annoncer
une autonomie cognitive ou à exécuter des outils externes.

## Prêt maintenant

- contrat de mission Pydantic ;
- runtime mono-étape honnête ;
- routeur avec cascade et coûts ;
- garde budgétaire monétaire ;
- oracle déterministe limité ;
- journal chaîné ;
- persistance snapshot PostgreSQL ;
- abandon explicite après crash ;
- CI PostgreSQL/Compose sur la PR #10.
- Plan/Step déterministe : versions, DAG, transitions, pré/postconditions,
  budgets, journal et restauration ; preuves dans `tests/test_plan_engine.py`.
- Cognitive Engine initial : objectif structuré, compilation, candidates,
  choix reproductible, observation, divergence et replanning sans replay ;
  preuves dans `tests/test_cognitive_engine.py` et
  `tests/test_phase31_hardening.py`.
- Phase 3.1 : conservation des suffixes et dépendances, coûts estimé/réservé/
  consommé, résultats partiels/incertains, persistance après révision et trois
  démonstrations JSON reproductibles dans `scripts/phase31_demo_*.py`.
- Phase 4 MVP : allowlist de six outils déterministes, permissions refusées par
  défaut, approbation d’écriture, validation de paramètres, idempotence,
  observation/vérification et restauration des actions ; preuves dans
  `tests/test_action_engine.py` et `scripts/phase4_demo_suite.py`.

## Non prêt

- compréhension libre, planner génératif et stratégie corrective riche ; le
  noyau déterministe borné est livré, mais sans autonomie générale ;
- outils externes, sandbox de processus et timeout matériel ;
- observation des effets externes ;
- stratégie corrective ;
- approbation humaine UI et reprise d’effets externes ;
- Memory Core persistant et intégré ;
- SkillCards promues par preuves runtime ;
- approbation humaine et sécurité d’outils ;
- expérience de valeur mesurée sans biais du LLM.
- concurrence multi-instance avec CAS/locking distribué ;

Les 122 tests locaux sont verts. Deux tests PostgreSQL sont skip lorsqu’aucune
`NEXUS_DATABASE_URL` n’est fournie ; cela ne constitue pas une preuve locale de
la CI PostgreSQL/Compose. Le CAS multi-writer PostgreSQL reste donc un gate
bloquant et le verdict demeure Foundation-Ready partiel.

## Gate avant outils externes ou effets non réversibles

Aucune exécution d’outil ne doit être ajoutée avant :

1. contrats Plan/Step/Action/Observation/Effect ;
2. policy d’autorité et permission explicite ;
3. sandbox et dry-run ;
4. préconditions/postconditions ;
5. idempotency keys ;
6. journal append-only ;
7. test d’arrêt forcé avant/après action ;
8. approbation humaine pour les effets non réversibles.

## Addendum Phase 4.1 — verdict de fiabilité

Phase 4.1 est **partiellement prouvée dans le périmètre déterministe local**. Les preuves ajoutées couvrent la conversion `running → interrupted_uncertain`, l’interdiction de rejeu, l’empreinte d’idempotence contextuelle, les exceptions inattendues, l’approbation sans démarrage, les limites de sortie, la concurrence entre deux exécuteurs in-process et un SIGKILL réel avec compteur de handler. Les six démonstrations sont générées par `scripts/phase41_demo_suite.py` dans `reports/phase4-1-demos/`.

Le verdict ne s’étend pas à un sandbox de processus, à un timeout interruptible, à un effet externe observable, ni à plusieurs writers PostgreSQL. `PostgresSnapshotStore` est explicitement single-writer par clé; son upsert ne constitue pas une preuve CAS multi-processus. Les deux tests PostgreSQL restent conditionnels à `NEXUS_DATABASE_URL`.

La validation locale Phase 4.1 exécutée sur la branche dédiée est verte : `122 passed, 2 skipped` (les deux skips exigent `NEXUS_DATABASE_URL`; ce nombre vaut pour cet environnement et cette révision).
