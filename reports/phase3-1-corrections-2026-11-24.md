# Rapport de corrections Phase 3.1 — 2026-11-24

## Base et périmètre

La branche `hardening/ciel-phase3-1-cognitive-reliability-2026-11-24` est issue exactement du commit Phase 3 `8f5c7ca5fa4b300ef009a50dee75af09abea5bf5`. Aucun changement n’est porté à `main`, aux PR #10/#11/#12, à Memory Core ou à la branche Phase 3.

## Corrections prouvées

| Défaut/scénario | Correction | Preuve |
|---|---|---|
| La replanification remplaçait `[s1,s2,s3]` par la seule correction | Les étapes vérifiées et les étapes futures valides sont conservées ; les dépendances vers l’échec sont réécrites vers la correction | `test_first_failure_preserves_remaining_steps_and_resumes_after_correction` |
| Perte du préfixe vérifié lors d’un échec intermédiaire | Préfixe vérifié conservé dans la nouvelle version | `test_intermediate_failure_preserves_verified_prefix_and_suffix` |
| Risque de replay d’une correction échouée ou étape incertaine | Transitions explicites ; `uncertain` ne peut pas redevenir `running` ; aucune exécution externe n’est rejouée | `test_failed_correction_stays_failed_and_is_not_replayed`, `test_uncertain_observation_is_suspended_and_never_replayed` |
| Budget correction non borné | Déduction du coût consommé et des budgets futurs ; refus si aucune réserve restante | `test_no_budget_for_correction_is_rejected` |
| Confusion estimation/réservation/consommation | Champs séparés et libération de la réservation à l’observation | `test_reserved_and_actual_costs_are_distinct` |
| Blocage non traçable | Événement `step_blocked` pour dépendance/précondition refusée | `test_precondition_rejection_is_journaled` |
| Inconnues rejetées systématiquement | Classification bloquante/non bloquante/vérifiable ultérieurement | tests cognitifs de classification et compilation |
| Stratégies insuffisamment différenciées | Trois candidats déterministes avec coûts, risques, dépendances, informations, réversibilité et justification | tests `test_cognitive_engine.py` |
| Restauration sans historique de révision | Snapshots de versions contiguës et restauration du plan révisé | `test_replanned_history_restores_after_restart` |

## Démonstrations

- `scripts/phase31_demo_nominal.py` → `reports/phase31-demo-nominal.json`
- `scripts/phase31_demo_error_replan.py` → `reports/phase31-demo-error-replan.json`
- `scripts/phase31_demo_interruption_restore.py` → `reports/phase31-demo-interruption-restore.json`

Les trois scripts sont déterministes, CORE_ONLY, sans Action Executor, sans outil externe et sans effet irréversible.

## Limites maintenues

Le CAS/locking distribué multi-writer PostgreSQL reste un bloqueur explicite. Les tests PostgreSQL locaux sont conditionnels à `NEXUS_DATABASE_URL`; leur absence produit deux skips justifiés, sans être présentée comme une validation PostgreSQL. Le Tool Registry et l’Action Executor de production restent hors périmètre.
