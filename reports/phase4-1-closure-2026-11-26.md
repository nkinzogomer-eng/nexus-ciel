# Clôture CIEL Phase 4.1

Date : 2026-11-26  
Branche : `hardening/ciel-phase4-1-reliability-recovery`  
Commit de départ : `6ee29e6207927eb7beaaaf3982542c450d310a37`  
Commit de clôture : à créer après validation finale

## Correctif A1

Le chemin de coordination entre deux instances distinctes d’`ActionExecutor` ne se contente plus de retourner un résultat en mémoire. Lorsque le second exécuteur récupère le résultat, `_copy_result_to_record()` met à jour son `ActionRecord`, un événement `action_coordination_replayed` est ajouté à son journal et `_changed()` déclenche son propre stockage. Le snapshot du second exécuteur contient donc le résultat terminal, qui reste disponible après restauration et ne provoque aucun nouvel appel handler.

## Coordination A3

La coordination est limitée à un même processus et à un registre `ToolRegistry` partagé. Elle utilise une `WeakKeyDictionary` liée à la durée de vie du registre, évite la réutilisation dangereuse d’un `id(registry)` et borne le cache à 1024 clés. Cette coordination ne prétend pas protéger plusieurs processus, machines ou writers PostgreSQL.

## Preuves

Le test `test_second_executor_persists_coordinated_result_and_restores_without_replay` couvre deux exécuteurs distincts, le stockage propre au second, l’événement de journal, la restauration et l’absence de second appel handler. Les tests de collision d’identité restent actifs.

Validation exécutée :

```text
122 passed, 2 skipped
```

Les deux skips exigent `NEXUS_DATABASE_URL` et correspondent aux tests PostgreSQL live et PostgreSQL SIGKILL. La restriction PostgreSQL multi-writer single-writer reste imposée et documentée.

La Phase 5 ne doit commencer qu’après commit et vérification de cette clôture. Aucun code Phase 5 n’est inclus dans cette clôture.
