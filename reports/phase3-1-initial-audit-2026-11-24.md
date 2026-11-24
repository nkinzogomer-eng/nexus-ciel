# Audit initial Phase 3.1 — Cognitive Engine Hardening

Date : 2026-11-24  
Base vérifiée : `8f5c7ca5fa4b300ef009a50dee75af09abea5bf5`  
Branche de travail : `hardening/ciel-phase3-1-cognitive-reliability-2026-11-24`  
PR #12, PR #10 et PR #11 : conservées ouvertes et intactes.

## Matrice d’audit

| Élément | État constaté | Défaut éventuel | Correction prévue |
|---|---|---|---|
| Goal Understanding | Contrat Pydantic séparant faits, inconnues et hypothèses | Les inconnues ne sont pas classées bloquantes/non bloquantes/vérifiables ; la cohérence sémantique est minimale | Ajouter une classification explicite et une demande de clarification structurée |
| Mission Compiler | Produit sous-objectifs et dépendances séquentielles | Dépendances fabriquées à partir de l’ordre, contraintes et critères peu validés | Valider résultats, critères, contraintes et dépendances sans convertir hypothèses en faits |
| Strategy Engine | Deux candidates stables (`direct-bounded`, `staged-verified`) | Génération trop fixe ; sélection ignore préconditions, risques, limites, durée et contraintes obligatoires | Étendre le contrat et le filtre de faisabilité avec scores expliqués |
| Decision Engine | Sélection déterministe ; conseil LLM haché | Aucun arbitrage explicite pour politique, mémoire, incertitude ou contraintes structurées | Ajouter une décision de sélection/rejet avec raisons et garde-fous |
| Plan/Step integration | Création et transitions via PlanEngine | `ControlledReplanner` conserve uniquement les étapes `verified` et la correction | Préserver les étapes planifiées/ready valides, leurs dépendances et budgets |
| Observation/Verification | Vérifie les postconditions `equals/not_equals/exists` | Assessment binaire succès/échec ; pas de partiel/incertain ; observation absente non distinguée | Ajouter les issues `partial`/`uncertain` et des preuves attendues explicites |
| Controlled Replanning | Nouvelle version append-only et nouvelle idempotency key | Reproduction : un plan `s1,s2,s3` après échec de `s1` devient seulement `controlled-correction` | Conserver `s2,s3`, invalider seulement les descendants dépendants et ajouter la correction |
| Persistence/Recovery | Snapshot atomique fichier, restauration cognitive et journal vérifié | Cross-validation cycle/plan/historique et état `running` après interruption insuffisante | Valider références, historique, budgets et absence de replay dangereux |
| Budget enforcement | Budgets plan/étape contrôlés sur coût réel | Pas de distinction estimation/réservation/consommation ; correction calculée sur somme des budgets déclarés | Ajouter coûts estimés/réservés/réels et vérifier le disponible après révision |
| Journal consistency | Journal chaîné et événements cognitifs persistés | Les rejets de précondition et classifications d’incertitude ne sont pas journalisés | Journaliser les refus, diagnostics, décisions et révisions avec contexte |

## Défaut bloquant reproduit

La reproduction suivante utilise uniquement le moteur local : un plan de trois
étapes est créé, la première est mise en échec, puis `ControlledReplanner` est
appelé. Le résultat constaté est :

```text
before= ['s1', 's2', 's3']
after= ['controlled-correction']
```

C’est un défaut **P0 fonctionnel** : des étapes obligatoires disparaissent de
l’historique courant et la mission peut être déclarée réussie sans les vérifier.
Il est rattaché à `nexus/cognitive/engine.py`, lignes 209–227 sur la base de
référence, où seules les étapes `status == "verified"` sont conservées.

## Défauts non bloquants pour le correctif minimal

La classification fine des inconnues, les issues partielles/incertaines et les
scores multi-critères sont importants mais peuvent être livrés progressivement.
Ils ne doivent pas masquer le correctif prioritaire de conservation des étapes.

## Limites conservées explicitement

Le CAS PostgreSQL multi-instance identifié en Phase 3 reste un blocage pour le
multi-writer distribué. Aucun Action Executor, Tool Registry de production,
replay automatique ou accès externe n’est introduit dans cette phase.
