# Audit ciblé Phase 2 — 2026-11-23

Référence auditée : `c1f75c3eaebc918ff400ec936f9da9f8e44ead0b`  
Branche auditée : `hardening/ciel-phase2-plan-step-2026-11-23`  
La branche Phase 2 et la PR #11 n'ont pas été modifiées. La Phase 3 travaille
sur une branche distincte depuis ce commit.

## Résumé

La Phase 2 est solide pour un runtime mono-instance et pour les snapshots
fichier atomiques, mais deux limites d'intégrité sont à traiter avant de
revendiquer une persistance multi-instance complète.

## Résultats par contrôle

| Contrôle | Résultat | Gravité | Conclusion |
|---|---|---:|---|
| Deux instances indépendantes | Pas de CAS sur `PostgresSnapshotStore.save`; deux writers peuvent charger v1 puis sauvegarder chacun v2 | **P1 bloquant multi-instance** | Aucun claim de concurrence distribuée ; ajouter version/ETag ou verrou transactionnel avant usage multi-writer |
| Cohérence journal/snapshot | Les mutations PlanEngine mettent à jour l’état avant l’événement ; les deux flushes successifs sont cohérents en cas normal | P2 | Testée par la suite Phase 2 et les restaurations |
| Interruption pendant persistance fichier | `FileSnapshotStore` écrit un `.tmp` puis utilise `replace`, évitant un JSON partiellement écrit | P2 faible | Garantie fichier raisonnable ; crash exact entre commit PostgreSQL et retour reste à tester en CI |
| Transitions autorisées | Tables explicites et tests de transitions/échecs présents | Aucun | Conforme |
| Snapshot Plan invalide | `PlanEngine.from_snapshot` valide Pydantic, l’historique, le DAG et les budgets | Aucun | Rejet déterministe |
| Journal restauré altéré | La Phase 2 reconstruisait le journal sans appeler `verify_chain()` | **P1 intégrité restauration** | Corrigé sur la branche Phase 3 : PersistentRuntime rejette une chaîne invalide |

## Preuves Phase 3

`tests/test_cognitive_engine.py::test_tampered_journal_snapshot_is_rejected`
prouve le nouveau rejet d'un snapshot dont le payload journal est modifié.
Les tests Phase 2 restent exécutés sans modification de leur branche d'origine.

## Décision

Le défaut CAS multi-instance reste explicitement hors périmètre de cette
implémentation cognitive initiale et constitue un gate avant une exécution
multi-writer ou un replay distribué. Il ne justifie pas de réécrire le routeur
ni d'introduire un outil externe dans cette phase. Le noyau cognitif s'appuie
sur une instance runtime et conserve ses décisions dans le snapshot et le
journal existants.
