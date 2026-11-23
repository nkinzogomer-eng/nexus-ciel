# Matrice des capacités CIEL — Foundation Hardening

Base vérifiée : hardening `74a8258`, parent PR #10 `322bfd3`, Memory Core
`d2aa828` inchangé.

| Capacité | État | Preuve | Manque principal |
|---|---|---|---|
| Mission Pydantic / API création | Disponible | `nexus/schemas`, `nexus/api`, tests Phase 0 | Pas de cycle de vie pause/approval |
| Runtime | Partiel | `nexus/core/runtime.py` | Une seule tentative routeur |
| Router / escalade | Disponible dans périmètre | `nexus/router`, tests Phase 1 | Pas de retry/circuit breaker |
| Budget monétaire | Disponible sur PR #10 | `MissionGuard`, tests budget, CI | Deadline/tokens/temps non généralisés |
| Vérification indépendante | Disponible mais limitée | `DeterministicOutputVerifier` | Oracles simples, pas sémantique complexe |
| Journal chaîné | Disponible | `MissionJournal`, tests intégrité | Ledger métier complet à étendre |
| Persistance PostgreSQL | Prouvée sur PR #10 CI | migrations, run 42051032012 | Snapshot JSON monolithique |
| Abandon après crash | Disponible | gate SIGKILL CI | Reprise sûre non implémentée |
| Outils exécutables | Absent | aucun `ActionExecutor` | Permissions/sandbox/postconditions |
| Plan/Step Engine déterministe | Disponible dans périmètre Phase 2 | `nexus/planning`, `tests/test_plan_engine.py`, 78 tests verts | Pas de planner LLM ni d’exécution |
| Goal Understanding / Mission Compiler | Disponible dans périmètre Phase 3 | `nexus/cognitive`, `test_simple_goal_compiles_into_mission` | Pas de compréhension libre non structurée |
| Strategy Engine déterministe | Disponible dans périmètre Phase 3 | comparaison stable de deux candidates, tests de budget | Pas d’optimisation générale ni fournisseur requis |
| Cognitive Decision Engine | Disponible dans périmètre Phase 3 | autorité `deterministic_core`, conseil LLM non mutatif | Policy complète et mémoire externe absentes |
| Observation / Verification Loop | Disponible dans périmètre Phase 3 | succès, divergence, décision de révision, journal | Pas d’observation du monde réel |
| Controlled Replanning | Disponible dans périmètre Phase 3 | nouvelle version, étapes vérifiées conservées, pas de replay | CAS multi-instance non résolu |
| Observation Engine | Absent | aucune observation d’effet | Résultat fournisseur non observation métier |
| Strategy Engine avancé | Partiel | moteur déterministe Phase 3 | Analyse fournisseur et stratégie corrective riche absentes |
| Human approval | Absent | aucun endpoint/contrat | Frontière d’autorité à construire |
| CORE_ONLY / sans LLM | Partiel, Plan/Step prouvé | PlanEngine sans appel externe, tests A–H | Mission déterministe complète absente |
| Memory Core | Prototype | modèles/repository in-memory | Pas PostgreSQL, runtime, restart |
| SkillCards | Prototype contractuel | corroboration dans modèles/tests | Extraction et contradictions absentes |
| Self-diagnostics | Partiel | `/health`, policy | Pas diagnostic plan/effets/limites |
| Telegram | Absent | aucune intégration | À concevoir après sécurité |

Une capacité n’est considérée Foundation-Ready que si son comportement est
prouvé par un test reproductible et si ses limites sont explicitement décrites.
