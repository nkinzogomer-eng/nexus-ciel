# Architecture Action Engine MVP — 2026-11-24

## Flux

`MISSION → UNDERSTAND → PLAN → SELECT ACTION → AUTHORIZE → EXECUTE → OBSERVE → VERIFY → ADAPT → RECORD`

`CognitiveEngine.execute_action()` exige que la demande corresponde à la mission, au plan, à l’étape et à `step.action_ref == tool:<name>`. Il réserve l’étape, délègue uniquement à `ActionExecutor`, transmet l’observation à `CognitiveEngine.observe()` puis laisse les postconditions déterminer le succès.

## Registre

`ToolRegistry` contient exclusivement des `ToolSpec` enregistrés avec handler interne déterministe. Aucun nom de fonction arbitraire, import dynamique, shell, navigateur ou réseau n’est accepté. Les outils ont schémas, permissions, risque, réversibilité, coût, timeout déclaré, règle d’idempotence, disponibilité et périmètre d’accès.

Outils MVP : `calculate`, `read_workspace`, `write_workspace`, `verify_workspace`, `simulated_failure`, `simulated_uncertain`.

## Persistance

Les demandes et états `requested`, `authorized`, `running`, `succeeded`, `failed`, `partial`, `uncertain`, `cancelled`, `rejected` sont persistés dans le snapshot runtime et reliés au journal mission. Une clé d’idempotence terminale retourne le résultat enregistré sans appeler le handler une seconde fois.

## Limites

Le timeout est une limite déclarative du contrat MVP ; aucun handler long ou fournisseur externe n’est autorisé. La reprise après interruption est contrôlée et ne déduit jamais qu’un effet externe a eu lieu. Le modèle de persistance reste single-writer ; le CAS PostgreSQL multi-writer n’est pas revendiqué.
