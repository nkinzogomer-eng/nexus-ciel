# Journal de reprise Nexus Ciel

## Point d’arrêt
- Phase 0: **VALIDÉE** par CI GitHub run 1, conclusion `success`.
- Phase 1: implémentée dans le commit `feat: implement Phase 1 adaptive router with provider health and acceptance tests`.
- La CI doit valider la Phase 1 avant toute Phase 2.

## Phase 0 livré et validé
- Contrats Pydantic, Event Bus in-process, State Graph, Mission Journal chaîné, Capability Registry.
- API minimale, tests d’acceptation, CI Python 3.12.

## Phase 1 livré
- Contrat ProviderAdapter, health checks et deux fournisseurs abstraits: Ollama/local et fournisseur secondaire.
- AdaptiveRouter avec cache sémantique, seuil de confiance, escalade et journal des décisions.
- Tests d’acceptation: fournisseur le moins coûteux suffisant, escalade tracée, indisponibilité et cache.

## Critère de sortie Phase 1
La mission doit utiliser l’étage le moins coûteux suffisant; toute escalade doit être tracée et justifiée; un fournisseur indisponible doit être retiré du routage.

## Suite bloquée par CI
Phase 2: mémoire indexée + Belzébuth. Ne pas l’implémenter si la CI Phase 1 est rouge.

## Règle de continuité
À chaque phase: code suivi, tests d’acceptation, CI verte, journal mis à jour, commit identifiable. En cas d’échec CI, corriger la cause puis relancer avant d’avancer.
