# Rapport Phase 2 — Plan/Step Engine déterministe

Date : 2026-11-23  
Branche : `hardening/ciel-phase2-plan-step-2026-11-23`

## Base et périmètre

La branche part exactement de `74a8258a41cbdf8b7c7472826062cbfb592d0126`,
le commit de hardening Foundation. Son parent est `322bfd3b1e8a0697e1d7c866ffbca2696f716c35` (PR #10 / finalization branch). Le Memory Core
`d2aa828d105ecb5091af3e75db9a8aef5ad3488a` n'est pas modifié. `main`, PR #10 et
le Memory Core ne sont pas des cibles de cette branche.

Le périmètre livré est strictement : création et versioning de plans,
représentation persistante des étapes, dépendances DAG, transitions explicites,
préconditions/postconditions déterministes, budgets d'étape et de plan,
journalisation de progression, détection de plans invalides et restauration
après redémarrage. L'engine n'exécute aucun outil, ne fait aucun appel LLM et
ne déclenche aucun réseau.

## Revue adversariale et corrections

- Les transitions sont des tables explicites ; une transition absente lève
  `InvalidPlanTransition`.
- La validation refuse les identifiants/ordinaux dupliqués, les dépendances
  absentes, les auto-dépendances, les cycles, les plans vides, les budgets
  incohérents et le dépassement de `max_steps`.
- Les révisions utilisent `expected_version`, conservent toutes les versions
  et refusent un writer obsolète par `ConcurrentPlanModification`.
- Les coûts estimés et réels sont contrôlés au niveau de l'étape et du plan ;
  l'observation ne peut pas dépasser le budget déclaré.
- Le journal est émis au moment de chaque mutation et le snapshot inclut toutes
  les versions. Les snapshots sont reconstruits par validation Pydantic.
- Le test concurrent a été corrigé pour capturer explicitement un succès et un
  conflit, plutôt que de laisser `pool.map` interrompre la preuve sur exception.
- Le test de redémarrage vérifie désormais aussi la restauration de l'historique
  après une révision, pas seulement la version courante.

## Preuves et scénarios obligatoires

| Scénario | Preuve |
|---|---|
| A — trois étapes dépendantes | `test_three_dependent_steps` et `scripts/plan_engine_demo.py` |
| B — échec d'étape | `test_failed_step` |
| C — précondition insatisfaite | `test_unsatisfied_precondition` |
| D — cycle | `test_circular_dependency` |
| E — redémarrage | `test_plan_persists_across_restart` |
| F — révision après observation | `test_revision_after_observation` |
| G — max-step/budget exhaustion | `test_max_steps_and_budget` |
| H — deux modifications concurrentes | `test_concurrent_revision_attempts_allow_only_one_writer` |

Validation locale dans un environnement virtuel neuf : **78 passed, 2 skipped**.
Les deux skips sont les tests PostgreSQL live et SIGKILL lorsque
`NEXUS_DATABASE_URL` n'est pas défini. La validation historique du commit de
hardening reste **69 passed, 2 skipped** ; elle ne remplace pas la CI de cette
nouvelle branche.

## Non-implémenté volontairement

Il n'y a pas de planner LLM, Strategy Engine, Action Executor, Tool Registry,
observation d'effet externe, idempotence d'appel, retry, recovery après effet
inconnu, approbation humaine, deadlines/tokens/temps, ou Memory Core persistant.
Ces éléments restent des gates avant toute capacité d'outil.

## Risques et prochains gates

Le snapshot demeure un document JSON monolithique et les budgets couvrent la
comptabilité déterministe de plan, pas la réservation d'un coût d'outil réel.
Le prochain gate est la CI PostgreSQL/Compose/SIGKILL sur le commit final de
cette branche ; un résultat CI de PR #10 ne sera pas réutilisé comme preuve.
Aucune fusion, rebase destructif, force-push ou modification de `main` n'est
prévue.
