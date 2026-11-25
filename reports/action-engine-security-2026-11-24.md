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
