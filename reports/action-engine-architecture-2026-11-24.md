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

## Addendum Phase 4.1 — Reliability, Crash Recovery & Execution Safety

Une action restaurée en `running` est convertie en `interrupted_uncertain`, terminal et non rejouable automatiquement. La décision est inscrite dans le journal par `action_recovery_blocked`. Les états `requested`, `authorized` (autorisé mais jamais démarré), `running`, `succeeded`, `failed`, `partial`, `uncertain`, `interrupted_uncertain`, `cancelled` et `rejected` sont distingués dans le contrat persisté.

L’identité d’idempotence est une empreinte SHA-256 canonique incluant mission, plan, étape, outil, paramètres, préconditions, permissions effectives, budget demandé, budget restant, limites d’entrée/sortie et versions de contrat. Une collision de clé est refusée; une clé terminale identique retourne le résultat enregistré. Le UUID local de `ToolSpec` n’est pas inclus car il est régénéré au redémarrage; le nom d’outil et la version du contrat sont stables.

Le handler est appelé après la persistance de `action_started`. Les exceptions déterministes de validation restent des échecs contrôlés; une exception inattendue, une interruption de processus ou une sortie impossible à classifier produit `interrupted_uncertain`. Les limites d’entrée/sortie sont effectives. Le timeout est observé après retour du handler et ne constitue pas une interruption matérielle.

La concurrence prouvée est celle d’un exécuteur partagé dans un processus. PostgreSQL reste explicitement single-writer: l’upsert atomique ne fournit pas un CAS multi-processus démontré.
