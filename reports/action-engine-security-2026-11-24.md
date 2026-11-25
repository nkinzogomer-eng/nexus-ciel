# Sécurité et permissions Action Engine MVP — 2026-11-24

## Contrôles

- allowlist stricte par `ToolRegistry` ; refus si l’outil n’existe pas ou est indisponible ;
- permissions explicites par outil ; absence de permission = refus ;
- approbation obligatoire pour l’écriture workspace et les outils à risque élevé ;
- validation des champs requis, types et clés inattendues ;
- budget d’action et budget restant contrôlés avant exécution ;
- idempotence persistée par clé ;
- résultat `uncertain` terminal et non rejoué ;
- journal des demandes, autorisations, démarrages, observations, refus et échecs ;
- workspace séparé, chemins relatifs uniquement, résolution canonique et interdiction de sortie du workspace.

## Périmètre effectif

`calculate` ne produit aucun effet externe. `read_workspace`, `write_workspace` et `verify_workspace` ne fonctionnent qu’avec un workspace explicitement configuré par l’appelant ; ils ne donnent aucun accès général au filesystem utilisateur. Les outils simulés servent exclusivement aux tests de récupération.

Aucun shell, commande système, navigateur, accès réseau, import arbitraire, plugin externe ou exécution de code utilisateur n’est enregistré.

## Non-affirmations

Le MVP ne fournit pas encore un sandbox de processus, un timeout matériel pour handlers longs, une approbation humaine UI ou un CAS distribué PostgreSQL. Ces limites sont maintenues explicitement.

## Addendum Phase 4.1 — exécution sûre et recovery

Les demandes portent maintenant une version de contrat et les records persistent une empreinte d’identité canonique ainsi que son contexte. Cette empreinte couvre les paramètres normalisés, préconditions, permissions, budgets/limites, mission, plan, étape et outil. Une même clé liée à un contexte différent est rejetée avant handler.

Une action `running` restaurée devient `interrupted_uncertain`; elle n’est jamais rejouée automatiquement. Les exceptions inattendues après démarrage sont classées conservativement, car l’absence d’observation ne prouve pas l’absence d’effet. Le journal conserve la décision de blocage. Les appels avant démarrage restent protégés par l’allowlist, permissions, approbation et budget.

Les limites de taille d’entrée et de sortie sont appliquées. Le timeout déclaré est mesuré après retour du handler; il ne tue pas un thread Python et ne fournit pas de sandbox de processus. Les tests SIGKILL réels mesurent les appels handler et démontrent la restauration sans second appel.

La concurrence multi-instance PostgreSQL n’est pas revendiquée. Le store est explicitement single-writer par clé de snapshot tant qu’un CAS transactionnel et son test multi-processus ne sont pas livrés.
