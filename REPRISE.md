# Journal de reprise Nexus Ciel

> Source de verite pour reprendre le projet. Une case n'est cochee que si le code et un test reproductible la justifient.

## Position actuelle

- Objectif: Nexus Ciel **interne d'abord**, auto-heberge sur un hote maitrise.
- Vision: Manas gele, capacites/politiques probatoires et reversibles, apprentissage hors mission, cascade economique, validation en couches.
- Dernier commit: `12e1587` (`fix: close four defects the green Phase 1 suite could not see`).
- Phase active: **Phase 1 close et durcie. Phase 2 ouverte, persistance d'abord, scaffold a fiabiliser avant preuve.**
- Suite d'acceptation: **46 tests** (33 heritees, 13 ajoutees en regression).

## Verite sur l'historique CI

- Run `#6` (`086ad85`): **annule**. Le groupe de concurrence `cancel-in-progress` l'a tue 11 secondes apres son demarrage, quand `9f9f545` a ete pousse.
- Run `#7` (`9f9f545`): **rouge**. `nexus/router/__init__.py` n'exportait pas `RoutingPolicy`, donc ImportError a la collecte: aucun test de Phase 1 ne s'est jamais execute.
- Run `#8` (`7d86b58`): **vert**. Correctif d'export et fermeture des ecarts de conformite.
- Correctif de fond dans `12e1587`: `cancel-in-progress` est desormais limite aux pull requests. Sur `main`, chaque commit va jusqu'a une conclusion. La cause racine de la confusion initiale est fermee, pas seulement son symptome.

Lecon retenue: un run annule n'est pas un run en cours. Verifier la conclusion, pas l'existence.

## Ce que la CI verte ne prouvait pas

`7d86b58` etait vert. Quatre defauts reels vivaient dessous, tous trouves en **executant** le systeme, aucun visible en le relisant. Corriges dans `12e1587`.

1. **Le Mission Journal etait falsifiable.** `verify_chain()` ne comparait que les pointeurs `precedent_hash`. Reecrire le `payload`, l'`actor` ou le `type` d'une entree en place laissait la chaine "valide". Un journal append-only qui ne detecte pas une modification de contenu prouve l'ordre, pas l'integrite. La signature est desormais recalculee sur le contenu complet a chaque verification, la continuite des `seq` est controlee, et `tampered_entries()` nomme les entrees fautives.
2. **Un hit de cache etait facture au prix de l'appel evite.** La decision de cache portait le `cost_usd` du resultat memorise: un hit gratuit rapportait 0.02 et `total_cost_usd` comptait deux fois un seul appel reel. Le pilotage economique, coeur du projet, mentait exactement au moment ou il economisait. Un hit coute 0.0 et enregistre `cost_avoided_usd`.
3. **Un fournisseur qui levait une exception tuait la mission.** `complete()` et `health()` etaient appeles sans garde: une `ConnectionError` d'un vrai Ollama traversait le Router. Pas d'escalade, pas de trace, pas de rapport FAIL. La cascade ne protegeait de rien des que les fournisseurs cessaient d'etre simules. Les deux appels sont contenus, l'echec devient une decision tracee `provider error`, et la cascade escalade.
4. **La surface HTTP contournait la cascade.** `nexus/api/app.py` construisait un `NexusRuntime()` nu: toute mission postee en HTTP renvoyait le verdict bouchon de Phase 0 pendant que la demo et les tests exercaient le Router. Le seul point d'entree qu'un humain appelle etait le seul a mentir. L'API partage maintenant le runtime route et expose `/policy` en lecture seule.

## Phase 0

- [x] Contrats Pydantic de base.
- [x] Event Bus in-process.
- [x] State Graph minimal.
- [x] Mission Journal append-only chaine **et infalsifiable** (`12e1587`).
- [x] Capability Registry probatoire.
- [x] API minimale, branchee sur la cascade (`12e1587`).
- [ ] Persistance PostgreSQL/Alembic et reprise apres crash reelle.
- [ ] Docker Compose reproductible.

Tout l'etat vit encore en memoire de processus. `MissionState.resumable_after_crash` vaut `True` alors que rien ne survit a un redemarrage: c'est le mensonge le plus couteux du prototype et il doit tomber en premier.

## Phase 1: routage economique

### Livre et prouve

- [x] Contrat fournisseur: `complete`, `health`, `cost_estimate`, `capabilities`.
- [x] Cascade officielle: cache, memoire, formel, outil, petit modele, grand modele, profond.
- [x] Politique versionnee reellement chargee depuis `policies/routing_policy_v1.json`, validee (schema, seuil, ordre de cascade, proprietaire, acces) et refusee si elle n'est pas `read_only`.
- [x] Le Router n'ecrit jamais la politique: test comparant octets et mtime avant/apres routage, plus objet gele.
- [x] Selection par rang de cascade puis par cout: l'ordre de declaration ne peut plus faire sauter un niveau moins cher.
- [x] Un fournisseur dont l'etage est hors politique n'est jamais appele.
- [x] `escalated` calcule sur les tentatives reelles.
- [x] Cle de cache incluant `critical`: une mission critique ne reutilise pas une reponse relachee.
- [x] Cache ignore si l'etage `cache` est retire de la politique.
- [x] **Un hit de cache est gratuit et declare ce qu'il a evite** (`12e1587`).
- [x] **Un fournisseur en panne ou qui leve escalade au lieu d'abandonner** (`12e1587`).
- [x] Telemetrie par appel: etage, rang, tentative, latence, tokens, cout, erreur, plus `trace()` auditable.
- [x] Echec borne et explicable (`RoutingExhausted`) nommant les fournisseurs ecartes et leurs erreurs.

### Critere PASS Phase 1: atteint

Le Router choisit le niveau le moins couteux suffisant, trace chaque escalade, ignore les fournisseurs indisponibles **ou defaillants**, echoue sans boucle si aucun resultat n'atteint le seuil, respecte la cascade officielle et ne facture que ce qui a ete depense.

### Reporte volontairement

- [ ] Remplacer les fournisseurs simules par Ollama/New-API derriere un AI Gateway reel. Le squelette de resilience existe (echec contenu, escalade); il manque retries bornes, timeout par appel et circuit breaker.
- [ ] Cache semantique Redis. Bloque tant que la persistance de Phase 0 n'existe pas.
- [ ] Telemetrie **persistante**. Aujourd'hui en memoire, perdue au redemarrage.
- [ ] **Budget non applique.** `Mission.constraints.budget_usd` est declare, transporte, et ignore. Rien n'arrete une escalade qui depasse le budget annonce. Meme famille de mensonge que `resumable_after_crash`. Releve du Mission Guard, Phase 3, et doit y etre traite explicitement.

## Ce qui tourne vraiment aujourd'hui

```bash
pip install -e '.[test]'
pytest -q
python -m nexus.demo "resume le sprint"
python -m nexus.demo "probleme dur" --local-confidence 0.3
python -m nexus.demo "panne locale" --local-unavailable
python -m nexus.demo "impossible" --local-confidence 0.1 --secondary-confidence 0.2
```

Une mission traverse reellement le State Graph, le journal chaine, l'Event Bus et la cascade economique, puis rend un rapport avec verdict, cout reel, cout evite et trace d'escalade.

Quatre scenarios verifies de bout en bout: le local suffit (cout 0), le local echoue et on escalade en payant, le local est hors ligne et on bascule, aucun niveau ne suffit et la mission finit `FAIL` / `abandoned` sans boucle. Le quatrieme n'etait atteignable que depuis un test: `--secondary-confidence` le rend accessible en ligne de commande, et la CI l'execute.

## Dette ouverte a traiter

- PR `#1` (`robin/phase1-routing-policy-telemetry`) est **obsolete**: elle visait les memes ecarts depuis `f78f38d` et est depassee deux fois par `main`. A fermer, pas a rebaser.
- Le zip historique `nexus-ciel-complete.zip` et les deux PDF de specification restent a la racine. Une seule arborescence canonique: les deplacer dans `docs/` ou les retirer.
- `tests/test_phase0_acceptance.py` et `test_regressions_phase1.py` partagent le `runtime` global de `nexus.api.app`. Tolerable aujourd'hui, a isoler par fixture des que la persistance arrive.
- Le cache du Router est global au processus et sans expiration: une reponse memorisee reste valide indefiniment. A borner en meme temps que le cache Redis.

## Prochaine etape: Phase 2

Ordre non negociable: **la persistance avant la memoire**. Construire un Memory Core sur un runtime qui perd tout au redemarrage revient a le construire deux fois.

### 2a. Fermer la persistance de Phase 0

Le scaffold de persistance existe desormais (snapshot store fichier/PostgreSQL, migration Alembic, compose), mais aucune case 2a ne sera cochee avant une PR verte et une preuve de reprise apres crash sur une execution reelle. Le blocage CI traite ici est la normalisation des DSN PostgreSQL: Alembic/SQLAlchemy doit accepter `postgresql://...` pour ouvrir `postgresql+psycopg://...`, sans casser `psycopg.connect()` cote runtime.

- [ ] Schema PostgreSQL et migrations Alembic pour State Graph, Mission Journal, Capability Registry, telemetrie de routage.
- [ ] Docker Compose reproductible (Postgres + API), une commande, sans etape manuelle.
- [ ] Test de reprise apres crash reel: tuer le processus en cours de mission, redemarrer, retrouver l'etat et une chaine de journal verifiee.
- [ ] Faire de `resumable_after_crash` une propriete calculee, jamais un litteral `True`.

### 2b. Memory Core et SkillCards

- [ ] Contrat Memory Core sans dupliquer les sources canoniques.
- [ ] SkillCard versionnee: contexte, methode, pieges, cout, taux de reussite, provenance, statut hypothese/confirmee.
- [ ] Adaptateur memoire deterministe en test d'abord, pgvector ensuite.
- [ ] Seuil strict, fraicheur, provenance, invalidation, souvenirs contradictoires.
- [ ] Brancher l'etage `memory` de la cascade sur le Memory Core: il est declare mais aucun fournisseur ne l'occupe.
- [ ] Belzebuth transforme les missions terminees en SkillCards, reussites comme echecs.
- [ ] Une SkillCard n'est confirmee qu'apres deux missions sources, jamais une seule.
- [ ] Test de reutilisation mesurant une baisse d'iterations ou de cout.
- [ ] Test prouvant que Belzebuth ne modifie jamais le Capability Registry.

## Roadmap restante

- Phase 3: Execution Fabric, Mission Guard (budget enfin applique), Validation Engine, rapports complets.
- Phase 4: Gymnase rejouable et Evolution Engine, 20 replays, +5%, veto regression, rollback.
- Phase 5: Capability Creation securise: oracle, second modele, sandbox niveau 3, probation, 10 succes.
- Phase 6: Great Sage conditionnel et Formal Reasoning deterministe.
- Phase 7: Redis Streams, OpenTelemetry, reprise sans perte et audit final.

## Regles de continuite

- Lire ce fichier avant toute modification.
- Une phase = code, tests d'acceptation, CI verte, checklist mise a jour, commit explicite.
- Verifier la **conclusion** du run CI, pas son existence: un run annule ne prouve rien.
- **Une suite verte prouve que les assertions ecrites tiennent, pas que le systeme marche.** Avant de fermer une phase, l'executer: falsifier une donnee censee etre protegee, debrancher un fournisseur, verifier que le cout rapporte correspond au cout paye, appeler la surface publique. Les quatre defauts de `12e1587` ont tous ete trouves ainsi.
- En CI rouge: corriger avant toute nouvelle phase.
- Une seule arborescence canonique; le zip historique reste une archive tant qu'il n'est pas retire par decision explicite.
- Aucun secret dans Git; aucune capacite generee ne peut ecrire dans `core/`.
- Ne jamais confondre prototype interne et production: interne n'autorise pas l'absence de garde-fous.
