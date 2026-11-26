# CIEL Phase 4.1 — Rapport final

Date : 2026-11-25  
Branche : `hardening/ciel-phase4-1-reliability-recovery`  
Base : `64466f8baec41c2a23c09f4779dfe98b4c924322`  
Dépôt : `https://github.com/nkinzogomer-eng/nexus-ciel`

## Verdict

Phase 4.1 est livrée sur la branche dédiée avec un verdict **partiellement prouvé et honnête**. Le périmètre déterministe local est durci et validé; aucune garantie non démontrée de sandbox de processus, timeout interruptible, effet externe observable ou CAS PostgreSQL multi-writer n’est revendiquée.

## Réponses aux dix critères du mandat

1. **Une action `running` restaurée peut-elle être rejouée ?** Non dans le périmètre corrigé. Elle devient `interrupted_uncertain`, un état terminal conservateur, reçoit l’événement `action_recovery_blocked` et retourne le résultat bloqué sans handler. Le test SIGKILL réel compte un seul appel.
2. **L’identité d’idempotence couvre-t-elle le contexte significatif ?** Oui : empreinte canonique SHA-256 de mission, plan, étape, outil, paramètres, préconditions, permissions, budget demandé, budget restant, limites et versions de contrat. Une collision est refusée.
3. **Une même demande et une même clé retournent-elles le résultat enregistré ?** Oui pour les états terminaux, y compris `uncertain` et `interrupted_uncertain`; le replay est marqué `idempotent_replay=True`.
4. **Une demande différente avec la même clé est-elle rejetée ?** Oui, avant handler, avec test des paramètres, budget, préconditions, permissions et version de contrat.
5. **Les exceptions et interruptions laissent-elles un état cohérent ?** Les erreurs déterministes pré-démarrage restent `rejected`/`failed`. Les exceptions inconnues après `action_started`, sorties impossibles à classifier, dépassements de sortie et interruptions de processus sont `interrupted_uncertain`; aucune reprise automatique dangereuse n’est autorisée.
6. **Les états jamais commencée, autorisée, commencée, terminée et inconnue sont-ils distingués ?** Oui via `requested`, `authorized` sans `started_at`, `running`, les états terminaux de succès/échec/partiel, `uncertain` et `interrupted_uncertain`. Le test d’approbation prouve `authorized` sans démarrage.
7. **La concurrence avec une même clé est-elle prouvée ?** Oui pour deux instances d’`ActionExecutor` partageant un registre contrôlé dans le même processus : un seul appel handler, un résultat original et un replay. La concurrence entre processus/runtime indépendants n’est pas revendiquée.
8. **Les budgets, permissions, réservations et cognitive loop restent-ils cohérents ?** Les contrôles de budget, permissions, approbation et préconditions sont conservés. `CognitiveEngine` transmet les états incertains à `observe()` et suspend au lieu de considérer l’action comme réussie ou de la relancer.
9. **PostgreSQL fournit-il un CAS multi-writer ?** Non prouvé. `PostgresSnapshotStore` est explicitement documenté `SINGLE_WRITER_ONLY`; l’upsert SQL est atomique mais ne compare pas une version attendue entre runtimes indépendants.
10. **CORE_ONLY et la sécurité de périmètre sont-ils préservés ?** Oui. Les handlers restent allowlistés et déterministes, sans fournisseur LLM obligatoire, shell, navigateur, réseau ou filesystem général. `calculate` et les tests cognitifs CORE_ONLY restent verts.

## Corrections principales

* ajout de `interrupted_uncertain`, `contract_version`, `identity_hash` et `identity_context`;
* recovery automatique des records `running` restaurés, avec journalisation et persistance;
* empreinte canonique stable entre redémarrages; l’UUID régénéré localement de `ToolSpec` n’est pas utilisé comme identité stable;
* transitions `authorized → running` persistées avant handler;
* classification conservatrice des exceptions inattendues et des résultats trop volumineux;
* limites effectives de 256 000 octets en entrée et 1 000 000 octets en sortie;
* intégration CognitiveEngine de l’état `interrupted_uncertain`;
* restriction single-writer PostgreSQL documentée dans le code et la matrice.

## Tests et démonstrations

Commande principale :

```bash
/tmp/ciel-phase2-venv/bin/python -m pytest -ra
```

Résultat : **121 passed, 2 skipped**. Les deux skips nécessitent `NEXUS_DATABASE_URL` et correspondent aux preuves PostgreSQL live et PostgreSQL SIGKILL; ils ne sont pas remplacés par des mocks.

Commandes complémentaires :

```bash
/tmp/ciel-phase2-venv/bin/python -m compileall -q nexus tests scripts
git diff --check
/tmp/ciel-phase2-venv/bin/python scripts/phase41_demo_suite.py
```

La suite produit six paires JSON/Markdown dans `reports/phase4-1-demos/` : mission nominale multi-actions, crash SIGKILL au milieu d’un handler, restauration sans rejeu, collision d’idempotence, exception inattendue et concurrence même clé. Chaque rapport contient objectif, environnement, étapes, événements, actions, nombre d’appels, résultats, vérifications et limites.

## Fichiers modifiés ou ajoutés

* `nexus/actions/models.py`, `nexus/actions/executor.py`;
* `nexus/cognitive/engine.py`;
* `nexus/persistence/postgres.py`;
* `docs/capability-matrix.md`, `docs/foundation-readiness.md`;
* `reports/action-engine-architecture-2026-11-24.md`, `reports/action-engine-security-2026-11-24.md`;
* `reports/phase4-1-initial-audit-2026-11-25.md`;
* `tests/test_phase41_reliability.py`, `tests/test_phase41_crash_recovery.py`;
* `scripts/phase41_demo_suite.py` et les douze rapports de démonstration.

PR #14, PR #13, PR #10, PR #11, PR #12, `main` et Memory Core n’ont pas été modifiés par cette branche.

## Limites restantes

Le handler Python n’est pas isolé dans un processus sandboxé; un timeout ne peut pas tuer un thread arbitraire et est observé après retour. La présence ou l’absence d’un effet externe n’est pas observable par les outils MVP. Les erreurs `RuntimeError`/`ValueError` déclarées déterministes sont classées `failed` selon les contrats actuels; un handler externe futur devra utiliser un contrat d’incertitude explicite après effet. PostgreSQL demeure single-writer jusqu’à preuve d’un CAS transactionnel multi-processus.
