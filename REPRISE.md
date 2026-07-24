# Journal de reprise Nexus Ciel

## Point d’arrêt
- Phase 0: **VALIDÉE**, CI run 1: `success`.
- Phase 1: code livré dans `59d97e2`.
- CI Phase 1: verdict non observable dans l’ancienne configuration; la CI a été durcie dans le commit `ci: make validation reproducible and observable for every phase`.

## Correctif CI
- Ajout de `workflow_dispatch` pour relancer manuellement.
- Permissions minimales `contents: read`.
- Annulation des runs obsolètes par branche.
- Timeout de 10 minutes.
- Cache pip et exécution explicite de `pytest -q`.

## Phase 1 livré
- ProviderAdapter, health checks, fournisseur local et secondaire.
- AdaptiveRouter avec cache, seuil de confiance et escalade tracée.
- Tests d’acceptation: coût minimal suffisant, escalade justifiée, fournisseur indisponible, cache.

## Contrôle de conformité en cours
- Le contrat global exige que le Router applique une politique versionnée, sans apprendre en direct.
- La version actuelle fournit un routeur fonctionnel mais encore en mémoire, sans politique YAML versionnée, télémétrie persistante, Redis ni AI Gateway.
- Ces écarts sont acceptables uniquement comme incrément Phase 1 et doivent être fermés avant la clôture complète de la Phase 1.

## Règle de progression
Ne pas commencer Phase 2 tant que la CI du dernier commit est verte et que les tests d’acceptation Phase 1 passent. Si la CI échoue, corriger la cause, pousser un commit correctif et relancer.

## Suite
Après validation Phase 1: Phase 2 = Memory Core indexé + Belzébuth, avec source de vérité unique, fiches de savoir-faire structurées, gestion des échecs et tests de réutilisation.
