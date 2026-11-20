# Architecture cible du moteur cognitif CIEL

**Statut :** conception Foundation Hardening, non implémentée.  
**Base de référence :** PR #10 `322bfd3`; Memory Core `d2aa828` reste un prototype séparé.

## Principes

CIEL reste propriétaire de la logique opérationnelle. Les LLM sont des
fournisseurs facultatifs pour proposer une décomposition, une stratégie ou un
texte ; ils ne décident jamais seuls de l’état de réussite, des permissions,
des coûts ou de la reprise.

Le fonctionnement `CORE_ONLY` doit être possible avec des règles déterministes,
des outils contrôlés et un moteur de vérification. `AI_ENABLED=false` doit
interdire les appels de modèles sans empêcher les missions déterministes.

## Flux cible

```text
Goal/Mission
    -> Mission Planner
    -> Plan + Steps
    -> Strategy Engine
    -> Policy/Safety + Budget Manager
    -> Action Executor -> Tool Registry
    -> Observation Engine
    -> Verification Engine
    -> Mission Ledger
       | PASS -> next step / completed
       | FAIL -> bounded correction or human intervention
       | uncertain -> Recovery Manager / abandon contrôlé
    -> Memory Core (derived, advisory, provenance-backed)
```

## Composants

### Goal / Mission

Entrée immuable de l’intention humaine ou système : objectif, contexte,
contraintes, deadline, budget, priorité, politique applicable et mode
`CORE_ONLY`/`AI_ENABLED`. Une mission ne contient pas de privilège implicite.

### Mission Planner

Transforme un objectif en plan versionné. Il doit produire des étapes bornées,
les dépendances, les préconditions, les postconditions, les risques et les
critères de terminaison. Toute proposition provenant d’un LLM est traitée comme
proposition non autorisée jusqu’à validation déterministe.

### Plan / Step

Le plan est un graphe acyclique versionné. Une étape possède un identifiant
stable, une clé d’idempotence, des entrées référencées, des préconditions, une
action autorisée, des observations attendues, une postcondition, un budget
restant et une politique de retry. Une étape ne peut être `succeeded` qu’après
observation et vérification.

### Strategy Engine

Sélectionne une stratégie parmi des règles ou des propositions de fournisseurs.
Il ne peut modifier ni la politique globale ni le registre d’outils. Les
révisions sont des versions append-only avec justification et déclencheur
observable.

### Action Executor

Seul composant autorisé à invoquer un outil. Il vérifie policy, permission,
préconditions, budget, deadline et idempotency key avant appel. Il capture le
résultat brut, le statut d’effet et l’erreur, sans déclarer la réussite métier.

### Tool Registry

Registre déclaratif de tools versionnés : schéma d’entrée/sortie, permissions,
mode dry-run, sandbox, réversibilité, coût, timeout, risques et postcondition.
Un tool inconnu ou non autorisé est refusé avant exécution.

### Observation Engine

Normalise les résultats de l’exécuteur en observations signées et datées.
L’observation indique sa source, son digest, son niveau de confiance et si elle
représente un effet confirmé ou seulement une réponse de transport.

### Verification Engine

Oracle indépendant. Il vérifie les postconditions d’étape puis les critères
de mission. Une réponse de modèle, une confiance ou une similarité mémoire ne
peut pas produire seule `PASS`.

### Memory Core

Stocke des faits dérivés, hypothèses, observations et SkillCards avec provenance
vers mission, report et journal. La mémoire est consultative, désactivable et
ne peut ni appeler un outil, ni modifier une policy, ni promouvoir une capacité.

### Mission Ledger

Évolution du Mission Journal actuel vers un ledger d’événements append-only :
plan versionné, décision, permission, appel outil, observation, vérification,
correction et recovery. Chaque effet externe doit être traçable par clé
d’idempotence et corrélé à une étape.

### Recovery Manager

Décide entre continuer, corriger, demander une intervention, réessayer ou
abandonner. Après crash, il ne reprend une étape que si l’état d’effet est
connu, la clé d’idempotence est stable et les préconditions sont revalidées.
Sinon il abandonne honnêtement ou demande une reprise humaine.

### Budget Manager

Gère budget monétaire, tokens, temps mur, deadline, nombre d’étapes, nombre de
retries et coût maximal d’un effet. Il réserve avant appel et réconcilie avec
le coût réel après appel. Tout dépassement est un échec explicite.

### Policy / Safety Engine

Autorité supérieure à planner, mémoire et fournisseur. Il contrôle mode
CORE_ONLY, AI_ENABLED, permissions, approbations, outils interdits,
sandbox, limites et arrêt d’urgence. Les politiques sont versionnées et
read-only pour les composants d’exécution.

### Self-Diagnostics

Expose santé des stores, chaîne du ledger, cohérence des plans, fournisseurs,
latence, budgets et outils. Les diagnostics sont des observations ; ils ne
peuvent pas s’auto-déclarer une mission réussie.

## Séquence nominale

1. Valider Mission et policy.
2. Construire un Plan versionné.
3. Vérifier chaque précondition et réserver les ressources.
4. Exécuter une seule étape autorisée.
5. Capturer l’effet et l’observation.
6. Vérifier la postcondition.
7. Journaliser avant de passer à l’étape suivante.
8. En cas d’échec, appliquer une correction bornée ou demander intervention.
9. Terminer seulement avec preuve de mission ou échec justifié.

## Séquence après crash

Le runtime recharge le ledger, identifie l’étape en vol et vérifie l’état de
tous les effets. Il ne rejoue jamais automatiquement une action dont l’effet
est incertain. Une reprise contrôlée exige : clé d’idempotence, préconditions
valides, budget restant, policy compatible et outil réentrant. Sinon la mission
est `abandoned` avec rapport `FAIL` et événement de recovery.
