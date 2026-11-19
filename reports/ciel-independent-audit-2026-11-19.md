# Audit indépendant et consolidation stratégique de Nexus CIEL

**Date :** 2026-11-19  
**Dépôt :** `nkinzogomer-eng/nexus-ciel`  
**Branche de revue :** `audit/ciel-independent-2026-11-19`  
**Main audité :** `3d8cf71b42ec9b3260768c5c454808bb450a153d`  
**PR #10 :** `322bfd3b1e8a0697e1d7c866ffbca2696f716c35`  
**Memory Core :** `d2aa828d105ecb5091af3e75db9a8aef5ad3488a`

## Verdict exécutif

CIEL n’est pas encore un système cognitif autonome long-courrier. Le dépôt
contient un noyau de runtime de mission crédible et honnête : modèle de mission,
graphe d’état, journal chaîné, registre de capacités probatoires, routeur de
fournisseurs, garde de budget, vérification déterministe limitée et persistance
snapshot. La PR #10 ajoute une candidate de finalisation sensiblement plus
complète, avec fournisseur OpenAI-compatible, budget cumulatif, vérification
explicite et gates PostgreSQL/Compose.

La capacité démontrée est toutefois une **exécution mono-étape d’une mission
vers une réponse de fournisseur, suivie d’un oracle de sortie borné**. Ce n’est
pas encore une boucle planifier → agir → observer → corriger → reprendre, ni un
moteur d’outils multi-étapes. Memory Core est un prototype contractuel en
mémoire, non une mémoire durable intégrée au runtime.

**Conclusion technique : NOT READY pour une finalisation autonome ou une
consolidation immédiate.** La PR #10 peut rester ouverte comme candidate isolée
à revue humaine. Aucune fusion ne doit être faite avant les phases de
finalisation décrites plus bas.

## 1. État réel du dépôt et des branches

### Préservation vérifiée

- Clone initial propre sur `main`.
- `main` local et distant : `3d8cf71b42ec9b3260768c5c454808bb450a153d`.
- PR #10 ouverte et en brouillon vers `main`.
- Aucun merge, force-push, reset destructif ou rebase effectué.
- Les branches `work/ciel-finalization-2026-11-05` et
  `work/ciel-memory-core-2026-11-05` n’ont pas été modifiées.
- Une branche locale de revue a été créée depuis `main` :
  `audit/ciel-independent-2026-11-19`.

### Références vérifiées

| État | HEAD vérifié | Relation |
|---|---|---|
| `main` | `3d8cf71b42ec9b3260768c5c454808bb450a153d` | base stable actuelle |
| PR #10 / `work/ciel-finalization-2026-11-05` | `322bfd3b1e8a0697e1d7c866ffbca2696f716c35` | 26 fichiers modifiés, +989/-71 par rapport à `main` |
| Memory Core / `work/ciel-memory-core-2026-11-05` | `d2aa828d105ecb5091af3e75db9a8aef5ad3488a` | dérivée de PR #10, puis +6 fichiers Memory Core |

Memory Core n’est donc pas une branche indépendante de `main` : elle contient
la totalité de la ligne PR #10 plus ses propres changements. Une consolidation
naïve des deux lignes risquerait de réappliquer les mêmes modifications.

### CI observée

- `main` HEAD `3d8cf71` : [run 32284621403](https://github.com/nkinzogomer-eng/nexus-ciel/actions/runs/32284621403), `success`.
- PR #10 HEAD `322bfd3` : [run 42051032012](https://github.com/nkinzogomer-eng/nexus-ciel/actions/runs/42051032012), `success`.
- Le journal détaillé du run PR #10 indique **71 tests passés en 1,97 s**, migrations PostgreSQL, gate SIGKILL, restauration Compose, smoke run et chemin non routable réussis.
- Aucun run CI distinct n’a été observé pour le HEAD Memory Core `d2aa828`.

### Exécution locale

Les dépendances ont été installées dans des environnements virtuels temporaires,
sans modifier le dépôt.

Les tests hors gates PostgreSQL/SIGKILL ont réussi dans les trois worktrees :

| État | Tests sélectionnés | Résultat |
|---|---:|---|
| `main` | 55 | tous passés |
| PR #10 | 67 | tous passés |
| Memory Core | 73 | tous passés |

L’exécution complète locale sans `NEXUS_DATABASE_URL` ne passe pas proprement :
`tests/test_phase2_postgres.py:15` accède directement à
`os.environ["NEXUS_DATABASE_URL"]` et produit `KeyError`. La gate SIGKILL est,
elle, marquée conditionnelle à cette variable. Docker, `psql`, `postgres` et
le port local 5432 n’étaient pas disponibles dans l’environnement d’audit.

Cette divergence ne contredit pas le run CI, qui dispose du service PostgreSQL,
mais elle signifie que la suite locale n’est pas autonome hors environnement
CI et que ce point doit être corrigé avant de présenter la validation comme
portable.

## 2. Matrice des capacités

Statuts utilisés : **OPERATIONAL**, **PARTIAL**, **PROTOTYPE**, **ABSENT**,
**NOT VERIFIED**.

| Capacité | État réel | Preuves examinées | Lacunes et risques |
|---|---|---|---|
| Contrat de mission | OPERATIONAL dans le périmètre Pydantic | `nexus/schemas/models.py`, tests Phase 0 | Aucun modèle de plan ou de sous-objectifs |
| Mission Runtime | PARTIAL | `nexus/core/runtime.py`, tests intégration | `accept()` exécute un seul appel routeur puis termine la mission |
| Goal/Mission management | PARTIAL | `Mission`, `StateGraph`, API `/mission` | Pas de décomposition, dépendances, file de missions ou orchestration longue |
| Mission Guard | OPERATIONAL pour le budget | `nexus/core/mission_guard.py`, `tests/test_mission_guard.py` | Deadline, tokens, itérations et temps ne sont pas bloqués |
| State Graph | OPERATIONAL minimal | `nexus/core/state_graph.py`, tests | Transitions libres et peu typées ; pas de graphe de plan ou de reprise |
| Mission Journal | OPERATIONAL comme journal chaîné volatile/snapshot | `nexus/core/mission_journal.py`, tests d’intégrité | Pas de télémétrie persistante détaillée ni de contrôle d’accès |
| Capability Registry | OPERATIONAL probatoire minimal | `nexus/core/capability_registry.py`, tests | Registre déclaratif ; aucune exécution d’outil, sandbox ou promotion réelle |
| Router | OPERATIONAL pour la cascade de fournisseurs | `nexus/router/router.py`, politique JSON, tests | Cache seulement en mémoire ; pas de retry/circuit breaker multi-profil |
| Provider local/synthétique | OPERATIONAL comme fixture de test | `nexus/providers/local.py`, démo et tests | Ne démontre pas une capacité cognitive réelle |
| Provider OpenAI-compatible | PARTIAL / prototype opérationnel | `nexus/providers/openai_compatible.py`, fake transport tests | Un seul endpoint configuré ; aucun appel modèle réel exécuté dans cet audit |
| Vérification de sortie | OPERATIONAL mais bornée | `nexus/core/verification.py`, tests | Vérifie des chaînes/JSON simples, pas la vérité sémantique d’un objectif complexe |
| API HTTP | PARTIAL | `nexus/api/app.py`, tests `httpx` | Création et lecture de mission seulement ; pas suspendre/annuler/reprendre/approval |
| Persistance fichier | OPERATIONAL comme snapshot local | `nexus/persistence/runtime.py` | Pas de transactions riches ni de migration de schéma du snapshot |
| Persistance PostgreSQL | VERIFIED sur PR #10 par CI | `PostgresSnapshotStore`, Alembic, run 42051032012 | Non exécutée localement faute de service ; un snapshot JSON monolithique |
| Récupération après crash | OPERATIONAL selon politique d’abandon contrôlé | `PersistentRuntime._reconcile_interrupted_missions`, SIGKILL gate CI | Ce n’est pas une reprise ; les missions sont abandonnées volontairement |
| Checkpoints | PARTIAL | runtime snapshots | Pas de checkpoint sémantique par étape, idempotence d’action ou reprise sûre |
| Outils/capacités exécutables | ABSENT | `ProviderCaps.tools` existe, aucune boucle d’appel outil | Permissions, isolation, réversibilité et post-vérification absentes |
| Planification multi-étapes | ABSENT | Recherche globale sans planner/subgoal/execution loop | Un objective devient directement le prompt fournisseur |
| Observation/correction de plan | ABSENT | Aucun module ou test correspondant | Pas de boucle autonome |
| Human approval | ABSENT | Aucun endpoint/service de validation | Risque d’action future sans frontière humaine définie |
| Mémoire durable | PROTOTYPE sur branche Memory Core | `nexus/memory/models.py`, `repository.py`, 6 tests | In-memory uniquement, pas de migration, pas de persistance/restart |
| Provenance Memory Core | PARTIAL contractuel | `MemoryProvenance`, SkillCard contract | Aucun lien runtime vérifié vers report/journal canonique |
| SkillCards | PROTOTYPE contractuel | `SkillCard`, tests de deux sources | Pas d’extraction, corroboration runtime, contradiction ou promotion intégrée |
| Intégration Memory au Router | ABSENT | `memory` existe seulement dans la liste de stages | Aucun repository injecté, aucune récupération dans le runtime |
| Retry/circuit breaker/fallback | PARTIAL | cascade et erreurs bornées du router | Fallback de fournisseurs existe ; retry borné et circuit breaker absents |
| CORE_ONLY / `AI_ENABLED=false` | PARTIAL | runtime sans router retourne `PARTIAL` ; factory vide sans config | Le système ne réalise pas une mission autonome sans LLM ; il s’abstient |
| Telegram | ABSENT | aucune intégration trouvée | Interface privée non définie |
| Docker Compose | VERIFIED sur PR #10 par CI | `docker-compose.yml`, run 42051032012 | Pas réexécuté localement faute Docker |

## 3. Revue de l’intelligence opérationnelle

Le scénario réellement implémenté est :

1. recevoir un objet `Mission` ;
2. créer un état `in_progress` ;
3. envoyer `mission.objective` à un routeur ;
4. éventuellement escalader entre fournisseurs ;
5. appliquer un oracle de sortie simple ;
6. produire `PASS`, `FAIL` ou `PARTIAL` ;
7. journaliser et persister le snapshot.

Les capacités suivantes ne sont pas implémentées :

- décomposer un objectif complexe en sous-objectifs ;
- construire un plan explicite ;
- exécuter plusieurs actions dépendantes ;
- appeler des outils avec permissions ;
- observer des effets du monde extérieur ;
- réviser un plan après observation ;
- reprendre une étape après interruption ;
- vérifier indépendamment l’atteinte d’un objectif sémantique.

La démo `nexus.demo` est explicitement synthétique. Elle produit un texte
`local:<objectif>` et passe grâce à l’oracle `contains_any`; elle ne constitue
pas une preuve d’autonomie ou d’exécution d’outil.

## 4. Revue des outils, sécurité et autorité

Le registre `CapabilityRegistry` décrit des capacités mais ne les exécute pas.
`ProviderCaps.tools` est un attribut de capacité, pas un moteur d’appel d’outil.
Aucun contrat observé ne définit simultanément : permission, isolation,
réversibilité, approbation humaine, journal des effets externes et vérification
post-action.

La configuration de production désactive correctement les fournisseurs
synthétiques par défaut et exige des prix explicites pour un endpoint hébergé.
Cela améliore l’honnêteté opérationnelle, mais ne transforme pas le provider
HTTP en agent autonome. Aucun endpoint externe réel n’a été appelé pendant cet
audit.

## 5. Revue complète de Memory Core

La branche Memory Core contient :

- modèles Pydantic de `MemoryProvenance`, `MemoryRecord`, `SkillCard` et
  `SkillStep` ;
- provenance avec digest de rapport, plage du journal et statut de validité ;
- repository mémoire déterministe avec idempotence par `extraction_key` ;
- expiration, invalidation explicite et filtrage de retrieval ;
- règle de corroboration d’une SkillCard par deux missions sources distinctes ;
- tests de contrat unitaires.

Elle ne contient pas :

- migration PostgreSQL Memory Core ;
- repository durable ;
- extraction automatique depuis les missions ;
- récupération après redémarrage ;
- contradiction event append-only ;
- invalidation liée à une nouvelle observation runtime ;
- intégration au `NexusRuntime` ;
- intégration réelle au stage `memory` du router ;
- mesure held-out de valeur avec/sans mémoire.

La documentation Memory Core est honnête et qualifie le travail de
spécification/contrat. Elle ne doit pas être présentée comme une mémoire
opérationnelle.

## 6. Comparaison et risques de conflit

### Main → PR #10

La PR #10 ajoute notamment :

- `MissionGuard` et budget cumulatif ;
- vérification déterministe ;
- provider OpenAI-compatible et factory de configuration ;
- changements runtime/API/router ;
- persistance Compose/PostgreSQL et scripts de gate ;
- 12 tests ou fichiers de tests/documentation associés.

Le risque principal est de considérer le run CI de PR comme une validation de
`main`. Les preuves sont valides pour `322bfd3`, pas pour `3d8cf71`.

### PR #10 → Memory Core

Memory Core ajoute six fichiers principaux :

- `docs/memory-core-skillcards-contract.md` ;
- `nexus/memory/__init__.py` ;
- `nexus/memory/models.py` ;
- `nexus/memory/repository.py` ;
- `tests/test_memory_core.py` ;
- mises à jour de `REPRISE.md`.

La branche est historiquement empilée sur PR #10. Il n’y a pas de conflit de
code majeur détecté dans les fichiers Memory eux-mêmes, mais toute intégration
future doit d’abord intégrer ou remplacer proprement la ligne PR #10, puis
ajouter Memory Core par étapes. Il ne faut pas cherry-pick la branche Memory
entière sur `main` sans analyse de parentage et de preuves.

## 7. Stratégie de consolidation proposée

Aucune consolidation ne doit être réalisée pendant cet audit.

### À conserver

- `main` comme base historique intacte ;
- PR #10 comme candidate cohérente de Phase 2/finalisation ;
- la politique d’abandon contrôlé après crash ;
- la séparation génération / vérification ;
- les tests de budget, de fournisseur et de persistance ;
- le contrat Memory Core comme spécification, pas comme capacité déclarée.

### À adapter avant toute intégration

- rendre les tests PostgreSQL explicitement skip-safe hors environnement configuré ;
- corriger les documents de `main` qui référencent encore `551116e` alors que
  `main` est `3d8cf71` ;
- définir un contrat runtime pour mission, étape, action, observation et effet ;
- définir une vraie frontière d’outil et d’approbation humaine ;
- introduire une persistance versionnée des étapes et idempotency keys avant
  toute reprise automatique ;
- concevoir Memory Core comme source consultative et non comme autorité.

### À ne pas fusionner maintenant

- Memory Core dans le runtime ;
- un planner LLM présenté comme autonomie ;
- des appels outil non sandboxés ;
- une reprise automatique après crash ;
- une interface Telegram avant définition des permissions et validations.

## 8. Plan de finalisation priorisé

### Phase A — Reproductibilité et base persistante

**Objectif :** obtenir une base de référence reproductible.  
**Tâches :** corriger le test PostgreSQL sans DSN, mettre à jour les documents
main, rejouer CI sur un commit candidat, conserver les logs PostgreSQL et
Compose.  
**Dépendances :** PR #10, PostgreSQL et Docker CI.  
**Difficulté/risque :** faible à moyenne ; risque de confondre snapshot et
checkpoint sémantique.  
**Acceptation :** tests hors DB passent avec skips explicites ; tests DB
échouent clairement si service absent et passent dans CI ; aucune affirmation
main/branch erronée.

### Phase B — Contrat d’exécution multi-étapes

**Objectif :** remplacer l’appel unique par un état d’étapes observable.  
**Tâches :** définir `Plan`, `Step`, `Action`, `Observation`, `Effect`, états
et transitions ; journaliser les identifiants idempotents.  
**Dépendances :** State Graph, Journal, persistence schema versioning.  
**Risque :** architecture trop couplée au LLM.  
**Acceptation :** une mission de trois étapes avec deux succès et une erreur
produit un trace complet, un état final explicite et aucune répétition après
relecture.

### Phase C — Outils et autorité

**Objectif :** exécuter un outil contrôlé, réversible et vérifiable.  
**Tâches :** capability contract exécutable, permissions, sandbox, dry-run,
approval humaine, timeout, compensation et postcondition.  
**Dépendances :** Phase B.  
**Risque :** effets externes irréversibles.  
**Acceptation :** outil de test simulé refusé sans permission, exécuté en
sandbox avec approval, puis vérifié par postcondition et journal.

### Phase D — Recovery sûre

**Objectif :** distinguer abandon contrôlé et reprise déterministe.  
**Tâches :** checkpoints par étape, idempotency keys, revalidation des
préconditions, reprise seulement des étapes prouvées sûres, budget restant et
limites d’itération.  
**Dépendances :** Phases B/C et persistance DB.  
**Risque :** double effet externe.  
**Acceptation :** SIGKILL avant/après chaque étape ; reprise sans duplication,
ou abandon explicite si l’état d’effet est incertain.

### Phase E — Memory Core durable et consultatif

**Objectif :** préserver l’acquis Memory sans lui donner d’autorité.  
**Tâches :** migration PostgreSQL, repository transactionnel, extraction
candidate depuis report/journal, contradiction, invalidation, retrieval avec
provenance, intégration read-only.  
**Dépendances :** source canonique Phase B et recovery Phase D.  
**Risque :** mémoire fausse ou fuite de données.  
**Acceptation :** deux missions indépendantes corroborent une SkillCard,
une contradiction la retire du retrieval, redémarrage conserve provenance et
le runtime fonctionne mémoire désactivée.

### Phase F — Valeur opérationnelle et interface privée

**Objectif :** démontrer une mission utile de bout en bout.  
**Tâches :** held-out tasks, mesure coût/temps/itérations, API lifecycle,
Telegram privé seulement après permissions et human approval.  
**Dépendances :** toutes les phases précédentes.  
**Risque :** surinterprétation des résultats synthétiques.  
**Acceptation :** rapport reproductible séparant qualité, coût, latence et
échecs ; aucune revendication générale sans comparaison indépendante.

## 9. Test final réaliste envisagé

Le test final doit utiliser un environnement local contrôlé et un outil
réversible, par exemple la création puis modification d’un fichier de travail
sandboxé :

1. soumettre une mission complexe en API ;
2. produire un plan de trois étapes explicites ;
3. demander une approbation humaine avant l’étape à effet ;
4. exécuter une étape de lecture, une étape de transformation et une étape de
   vérification ;
5. enregistrer les observations et postconditions ;
6. provoquer une erreur contrôlée sur l’étape 2 ;
7. vérifier que le plan est révisé sans répéter l’étape 1 ;
8. tuer le processus à plusieurs points déterministes ;
9. redémarrer et revalider les préconditions avant reprise ou abandon ;
10. extraire une mémoire candidate avec digest de report et plage de journal ;
11. redémarrer PostgreSQL/Compose et vérifier la conservation ;
12. produire un rapport final séparant PASS de chaque sous-étape, coût, durée,
    provenance, erreurs et décision de reprise.

Ce scénario ne doit pas appeler un système externe irréversible et ne doit pas
utiliser un LLM comme oracle de sa propre réussite.

## 10. Éléments non vérifiés

- appel réel à un endpoint LLM pendant cet audit ;
- Telegram ;
- exécution réelle d’outils externes ;
- reprises automatiques sûres ;
- Memory Core durable ;
- performance sur plusieurs heures ;
- circuit breaker, retries et profils multi-fournisseurs en production ;
- sécurité sandbox/permissions sur effets réels ;
- valeur généralisable de la stratégie cognitive.

## Recommandation finale

Conserver `main`, PR #10 et Memory Core séparés. Ne fusionner aucune branche
pendant cette mission. Utiliser PR #10 comme candidat technique pour la base
persistante, traiter Memory Core comme contrat/prototype à préserver, puis
commencer une nouvelle phase explicitement dédiée à l’exécution multi-étapes,
aux outils et à la récupération sûre.
