# Audit Phase 5 — Cognitive & Operational Intelligence

Date : 2026-11-26  
Branche auditée : `feature/ciel-phase5-cognitive-operational-intelligence`  
Base : `51e297250d5af1648023bf05c90410af1b165390`  
Dépôt : `nkinzogomer-eng/nexus-ciel`

## État initial vérifié

Le worktree était propre sur la branche Phase 5, issue de la clôture Phase 4.1. La suite locale collecte 122 tests, dont deux tests PostgreSQL conditionnels. La PR #15 est toujours ouverte, draft, sans statut de checks publié par GitHub au moment de l’audit (`statusCheckRollup: []`). Elle n’a pas été modifiée.

Le fichier `PRISM_Mandat_Finalisation.md` a également été relu : il prescrit explicitement de ne pas modifier Nexus CIEL. Le mandat applicable à cette branche est donc le mandat CIEL contenu dans `pasted_content.txt`.

## Matrice de capacité

| Exigence Phase 5 | État au départ | Preuve inspectée | Lacune bloquante | Périmètre retenu |
|---|---|---|---|---|
| Compréhension naturelle | Absente pour le cœur cognitif | `GoalUnderstanding` accepte déjà un contrat structuré ; `MissionCompiler` compile ce contrat | Aucune conversion bornée d’un texte naturel en contrat | Ajouter un parseur déterministe borné, explicite et abstentionniste |
| Faits / hypothèses / inconnus / décisions | Partielle | `known_facts`, `unknowns`, `hypotheses`, `CognitiveDecision` existent | Pas de provenance unifiée ni de distinction explicite à l’entrée | Ajouter un contrat d’analyse d’entrée sans transformer une supposition en fait |
| Ambiguïtés et contradictions | Partielle | validation de budget, résultats interdits et informations manquantes | Pas de détection dédiée de formulations ambiguës/contradictoires | Détecter quelques motifs déterministes ; bloquer seulement les ambiguïtés de sécurité/budget |
| Décomposition | Disponible dans le périmètre déterministe | `MissionCompiler`, `PlanEngine`, dépendances et préconditions | Décomposition naturelle non reliée au compilateur | Réutiliser le compilateur après normalisation ; ne pas créer un second planner |
| Stratégie | Disponible mais prédéfinie | trois candidats déterministes, scores et justifications | Ce n’est pas une intelligence adaptative générale | Exposer les limites ; utiliser la réévaluation/replanning existante après échec |
| Outils contrôlés | Disponible dans le périmètre Phase 4.1 | `ToolRegistry.deterministic`, allowlist, permissions, limites, workspace confiné | Pas d’accès libre autorisé, ce qui est conforme au mandat | Réutiliser `calculate`, lecture/écriture/vérification workspace ; aucune navigation/shell |
| Approbation humaine | Temporaire en mémoire | `ActionExecutor` lève `ApprovalRequired`, `ActionRecord.approved` existe | Aucun état de demande/expiration restauré | Ajouter un store d’approbation durable, lié à l’empreinte d’action |
| Observation indépendante | Partielle mais réelle | `PlanEngine` vérifie les postconditions ; `DeterministicOutputVerifier` vérifie des oracles explicites | Pas d’observateur séparé pour chaque adaptateur externe | Réutiliser les postconditions et rendre la preuve explicite dans les rapports |
| Restauration | Disponible dans le périmètre prouvé | snapshots atomiques, recovery `interrupted_uncertain`, pas de rejeu automatique | Reprise métier automatique non autorisée | Préserver l’abandon conservateur et tester les autorisations restaurées |
| CORE_ONLY / AI_ENABLED=false | Disponible | mode par défaut `CORE_ONLY`, factory providers vide sans configuration | Aucun fournisseur obligatoire | Ne pas ajouter de dépendance LLM ni de chemin obligatoire |
| Mémoire apprenante | Hors périmètre | aucun `nexus/memory` opérationnel à l’emplacement inspecté | Construire une mémoire complète serait contraire au mandat | Ne pas l’ajouter ; persister uniquement les états d’approbation liés aux actions |
| PostgreSQL multi-writer | Non prouvé | documentation Phase 4.1 et `PostgresSnapshotStore` | CAS multi-writer absent | Conserver la restriction single-writer |

## Changements indispensables retenus

1. Introduire une frontière d’entrée naturelle déterministe et bornée, avec résultat `accepted` ou `needs_clarification`, et des catégories de provenance explicites.
2. Rejeter ou signaler les formulations qui ne permettent pas de produire un contrat sûr ; continuer sans question pour les inconnues non bloquantes.
3. Ajouter une approbation durable, avec empreinte canonique de l’action, statut, expiration et validation stricte au redémarrage. Le cœur d’exécution restera `ActionExecutor`.
4. Ajouter les tests unitaires, CORE_ONLY, intégration/persistance et les démonstrations reproductibles. Les démonstrations distingueront clairement les outils déterministes locaux des effets externes réels.
5. Mettre à jour la matrice de capacités et le rapport de limites. Ne pas présenter le parseur borné comme une compréhension générale du langage naturel, ni les outils workspace comme une sandbox de processus.

## Décisions de sécurité

- Aucun shell arbitraire, accès général au filesystem, navigateur libre ou appel réseau ne sera ajouté.
- Une action sensible reste impossible sans permission et approbation valide.
- Une recommandation LLM, si configurée, restera non autoritative.
- Une action `running`, `uncertain` ou restaurée ne sera jamais rejouée automatiquement.
- Les résultats simulés resteront étiquetés comme simulations ; aucune preuve opérationnelle réelle ne sera revendiquée.
