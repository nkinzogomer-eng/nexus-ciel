# Rapport Phase 3 — Cognitive Engine Initial

Date : 2026-11-23  
Base exacte : `c1f75c3eaebc918ff400ec936f9da9f8e44ead0b`  
Branche : `cognitive/ciel-engine-phase3-2026-11-23`  
PR Phase 2 #11 : conservée ouverte et inchangée.

## Livré

Le noyau `nexus.cognitive` ajoute :

- `GoalUnderstanding` : objectif, résultats attendus, contraintes, critères,
  limites, faits connus, inconnues, hypothèses et confiance ;
- `MissionCompiler` : sous-objectifs, dépendances, contraintes et informations
  manquantes, avec refus des missions incohérentes ;
- `StrategyEngine` : candidates structurées, comparaison par score/coût/nom et
  choix reproductible ;
- `CognitiveDecisionEngine` : autorité finale `deterministic_core` ; un conseil
  LLM est seulement haché et ne peut pas muter l’état ;
- boucle `PLAN -> DECIDE -> OBSERVE -> VERIFY -> ADAPT -> RECORD` ;
- `ControlledReplanner` : nouvelle version, conservation des étapes vérifiées,
  nouvelle étape de correction et interdiction du replay ;
- snapshot/restauration des cycles cognitifs via `PersistentRuntime` ;
- événements cognitifs dans le Mission Journal existant.

Aucun outil externe, appel réseau, commande système, LLM obligatoire ou effet
irréversible n’est utilisé.

## Audit Phase 2

Le rapport détaillé est [`phase2-audit-2026-11-23.md`](phase2-audit-2026-11-23.md).
Deux limites sont classées P1 : absence de CAS entre instances PostgreSQL
indépendantes et absence initiale de validation du journal restauré. La seconde
est corrigée dans cette branche : `PersistentRuntime` rejette désormais une
chaîne altérée. La première reste un gate explicite avant une utilisation
multi-writer distribuée ; elle ne justifie pas une réécriture du routeur.

## Tests obligatoires

| Scénario | Preuve |
|---|---|
| A — objectif simple vers mission | `test_simple_goal_compiles_into_mission` |
| B — objectif ambigu/incomplet | `test_ambiguous_or_incomplete_goal_is_rejected` |
| C — comparaison de deux stratégies | `test_two_strategies_are_compared_deterministically` |
| D — choix reproductible | même test, deux sélections identiques |
| E — observation confirmant une étape | `test_cognitive_cycle_observation_confirms_step` |
| F — observation contredisant hypothèse | `test_observation_contradicting_hypothesis_is_failure` |
| G — échec puis révision | `test_failure_can_trigger_controlled_replanning_without_replay` |
| H — budget insuffisant | `test_budget_insufficient_for_strategy` |
| I — CORE_ONLY sans LLM | `test_core_only_cycle_does_not_need_llm` |
| J — LLM indisponible/réponse non autoritaire | `test_invalid_llm_recommendation_cannot_change_internal_choice` |
| K — restart/restauration | `test_cognitive_cycle_restores_after_restart` |
| L — proposition LLM sans mutation | même test, autorité déterministe et digest consultatif |

Validation locale finale : **91 passed, 2 skipped**. Les deux skips sont les
scénarios PostgreSQL live et SIGKILL sans `NEXUS_DATABASE_URL` local.

Démonstration complète : [`scripts/cognitive_engine_demo.py`](../scripts/cognitive_engine_demo.py).
Elle couvre observation inattendue, décision de révision, nouvelle version,
correction vérifiée et restauration avec journal valide.

## Limites restantes

Le moteur ne comprend pas du texte libre de façon générale, ne vérifie pas le
monde réel, ne possède pas de Tool Registry/Action Executor, ne fournit pas de
policy engine complet, ne fait pas de retry/recovery idempotent et ne résout
pas le CAS multi-instance. `CORE_ONLY` est prouvé pour les missions
structurées simples, pas pour toutes les missions complexes.

## Maturité honnête

CIEL est désormais **Plan/Step-ready et Cognitive-Engine initial-ready** dans
un périmètre déterministe et testable. Il n’est pas autonome sur des outils,
n’est pas Cognitive-Engine complet et ne doit pas être présenté comme un agent
opérationnel sur le monde extérieur.
