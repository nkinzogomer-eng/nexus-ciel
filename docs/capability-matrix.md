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
| Abandon après crash | Disponible dans le périmètre prouvé | test SIGKILL réel Phase 4.1, `interrupted_uncertain`, journal de recovery | Reprise automatique interdite; vérification métier requise |
| Outils exécutables | Disponible dans périmètre Phase 4.1 | allowlist, empreinte canonique, non-rejeu `running`, exceptions conservatrices, limites entrée/sortie, snapshots | Approbation UI, sandbox de processus, timeout interruptible et CAS multi-writer absents |
| Plan/Step Engine déterministe | Disponible dans périmètre Phase 2 | `nexus/planning`, `tests/test_plan_engine.py`, 78 tests verts | Pas de planner LLM ni d’exécution |
| Goal Understanding / Mission Compiler | Disponible dans périmètre déterministe Phase 3 | `nexus/cognitive`, tests de compilation et `reports/phase5-audit-2026-11-26.md` | La compréhension naturelle reste bornée, non générale |
| Strategy Engine déterministe | Disponible dans périmètre Phase 3.1 | trois stratégies différenciées, score justifié, filtres budget/contraintes/informations | Pas d’optimisation générale ni fournisseur requis |
| Cognitive Decision Engine | Disponible dans périmètre Phase 3 | autorité `deterministic_core`, conseil LLM non mutatif | Policy complète et mémoire externe absentes |
| Observation / Verification Loop | Disponible dans périmètre Phase 3.1 | succès, échec, partiel, incertain, coûts réservé/consommé | Pas d’observation du monde réel |
| Controlled Replanning | Disponible dans périmètre Phase 3.1 | suffixe conservé, dépendances réécrites, budget restant, historique, pas de replay | CAS multi-instance non résolu |
| Observation Engine | Absent | aucune observation d’effet | Résultat fournisseur non observation métier |
| Strategy Engine avancé | Partiel | moteur déterministe Phase 3 | Analyse fournisseur et stratégie corrective riche absentes |
| Human approval | Disponible dans périmètre Phase 5 | `ApprovalLedger`, `tests/test_phase5_approval.py`, snapshot/restart | Pas d’UI d’approbation ni identité externe ; l’approbateur est un identifiant applicatif |
| CORE_ONLY / sans LLM | Disponible dans périmètre Phase 4 MVP | cycle cognitif avec `calculate`, vérification et démonstration JSON | Outils externes et autonomie prolongée hors périmètre |
| Natural goal boundary | Disponible dans périmètre borné Phase 5 | `NaturalGoalInterpreter`, `tests/test_phase5_natural.py`, `scripts/phase5_demo_suite.py` | Motifs explicites seulement ; abstention sur ambiguïté bloquante ; pas de compréhension générale |
| Tool Registry / Action Executor | Disponible dans périmètre Phase 4.1 | allowlist, empreinte d’identité canonique, non-rejeu `running`, recovery et concurrence in-process | Approbation UI, sandbox de processus, timeout interruptible et CAS multi-writer absents |
| Memory Core | Hors périmètre Phase 5 | aucun composant de mémoire apprenante ajouté | Pas d’apprentissage long terme ni de mémoire générale |
| SkillCards | Prototype contractuel | corroboration dans modèles/tests | Extraction et contradictions absentes |
| Self-diagnostics | Partiel | `/health`, policy | Pas diagnostic plan/effets/limites |
| Telegram | Absent | aucune intégration | À concevoir après sécurité |

Une capacité n’est considérée Foundation-Ready que si son comportement est
prouvé par un test reproductible et si ses limites sont explicitement décrites.

Les tests PostgreSQL restent conditionnels à `NEXUS_DATABASE_URL` ; l’absence
de cette variable justifie les deux skips de la suite locale. Le CAS entre
writers multi-instance PostgreSQL demeure un bloqueur documenté.
