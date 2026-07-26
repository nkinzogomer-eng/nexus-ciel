# Journal de reprise Nexus Ciel

> Source de verite pour reprendre le projet. Une case n'est cochee que si le code et un test reproductible la justifient.

## Position actuelle

- Objectif: Nexus Ciel **interne d'abord**, auto-heberge sur un hote maitrise.
- Vision: Manas gele, capacites/politiques probatoires et reversibles, apprentissage hors mission, cascade economique, validation en couches.
- Dernier commit `main` observe: `a9e9ab6` (`docs: close Phase 1 on a green CI run and hand off to Phase 2`).
- CI observee sur `main`: check `tests` du commit `a9e9ab6` **completed/success** (demarre `2026-07-26T13:57:30Z`, termine `2026-07-26T13:57:46Z`).
- Phase active: **Phase 2 ouverte. Chantier en cours: fondations de persistance et reprise apres crash, sans valider encore la phase.**

## Verite sur l'historique CI

La consigne precedente attendait un run vert sur `086ad85`. Ce run n'a jamais pu conclure:

- Run `#6` (`086ad85`): **annule**. Le groupe de concurrence `ci-${{ github.ref }}` avec `cancel-in-progress` l'a tue 11 secondes plus tard, quand `9f9f545` a ete pousse.
- Run `#7` (`9f9f545`): **rouge**. `tests/test_phase1_acceptance.py` faisait `from nexus.router import AdaptiveRouter, RoutingPolicy` alors que `nexus/router/__init__.py` n'exportait pas `RoutingPolicy`. ImportError a la collecte: **aucun test de Phase 1 ne s'est jamais execute**.
- Run `#8` (`7d86b58`): **vert**. Correctif d'export plus fermeture des ecarts de conformite.
- Check `tests` sur `a9e9ab6`: **vert**. La documentation Phase 1/2 sur `main` est coherente avec l'etat du depot.

Lecon retenue: un run annule n'est pas un run en cours. Verifier la conclusion du run, pas seulement son existence.

## Phase 0

- [x] Contrats Pydantic de base.
- [x] Event Bus in-process.
- [x] State Graph minimal.
- [x] Mission Journal append-only chaine.
- [x] Capability Registry probatoire.
- [x] API minimale et rapport PASS.
- [ ] Persistance PostgreSQL/Alembic et reprise apres crash reelle.
- [ ] Docker Compose reproductible.

Tout l'etat vit encore en memoire de processus tant qu'aucun store durable n'est configure. `MissionState.resumable_after_crash` n'a plus le droit de mentir: il reste `False` en runtime ephemere et ne passe a `True` que dans le chemin persistant.

## Phase 1: routage economique

### Livre et prouve dans `7d86b58` (CI verte)

- [x] Contrat fournisseur: `complete`, `health`, `cost_estimate`, `capabilities`.
- [x] Cascade officielle declaree: cache, memoire, formel, outil, petit modele, grand modele, profond.
- [x] Politique versionnee **reellement chargee** depuis `policies/routing_policy_v1.json` par `nexus.router.policy`, validee (schema, seuil, ordre de cascade, proprietaire, acces) et refusee si elle n'est pas `read_only`.
- [x] Le Router n'ecrit jamais la politique: test comparant octets et mtime du fichier avant/apres routage, plus objet gele.
- [x] Selection par rang de cascade puis par cout: l'ordre de declaration des fournisseurs ne peut plus faire sauter un niveau moins cher.
- [x] Un fournisseur dont l'etage est hors politique n'est jamais appele.
- [x] Cache, health checks et escalade avec justification.
- [x] `escalated` calcule sur les tentatives reelles, plus sur l'index de liste.
- [x] Cle de cache incluant le drapeau `critical`: une mission critique ne reutilise pas une reponse produite en conditions relachees.
- [x] Cache ignore si l'etage `cache` est retire de la politique.
- [x] Telemetrie par appel: etage, rang, tentative, latence, tokens, cout, plus `trace()` auditable.
- [x] Echec borne et explicable (`RoutingExhausted`) nommant les fournisseurs ecartes.
- [x] Tests d'acceptation: 15 en Phase 1, 12 sur la politique, 6 en integration bout en bout.

### Critere PASS Phase 1: atteint

Le Router choisit le niveau le moins couteux suffisant, trace chaque escalade, ignore les fournisseurs indisponibles, echoue sans boucle si aucun resultat n'atteint le seuil, et respecte la cascade officielle. Verifie par la CI, pas par relecture.

### Reporte volontairement

- [ ] Remplacer les fournisseurs simules par Ollama/New-API derriere un AI Gateway reel (retries bornes, circuit breaker, fallback).
- [ ] Cache semantique Redis. Bloque tant que la persistance de Phase 0 n'existe pas.
- [ ] Telemetrie **persistante**. Elle est aujourd'hui en memoire, donc perdue au redemarrage.

## Phase 2: fondations posees dans cette branche, phase non validee

### Livre et prouve par les tests de cette branche

- [x] `MissionState.resumable_after_crash` n'est `True` que sur le chemin durable; le runtime purement memoire reste explicitement non resumable.
- [x] Store deterministe sur fichier capable de recharger etats, rapports, journal et registre apres restart.
- [x] Reprise minimale prouvee apres crash en milieu de mission: une mission acceptee reste visible `in_progress` apres redemarrage du runtime persistant.
- [x] Composition additive hors `core/`: `PersistentRuntime` et stores externes branchent la durabilite sans ecrire dans Manas/Core.
- [x] Fondation PostgreSQL/Alembic ajoutee: table de snapshot JSONB, migration initiale, factory de runtime, `Dockerfile` et `docker-compose.yml`.

### Ce qui reste avant de cocher Phase 0 persistance / Docker Compose

- [ ] Prouver en CI une restauration **sur PostgreSQL reel** (pas seulement store fichier) avec migration Alembic appliquee.
- [ ] Ajouter une preuve reproductible que `docker compose up --build` restaure un etat deja present dans le volume `postgres_data`.
- [ ] Decider si le snapshot unique JSONB reste suffisant ou s'il faut passer a des tables normalisees avant la memoire Phase 2.
- [ ] Prevoir la reprise des missions inachevees apres crash (rejouer/abandonner explicitement), pas seulement leur presence persistante.

## Ce qui tourne vraiment aujourd'hui

```bash
pip install -e '.[test]'
pytest -q
python -m nexus.demo "resume le sprint"
```

Une mission traverse reellement le State Graph, le journal chaine, l'Event Bus et la cascade economique, puis rend un rapport avec verdict, cout reel et trace d'escalade. `NexusRuntime(router=...)` execute par la cascade; sans router il garde le comportement trivial de Phase 0.

En branche persistance, quatre scenarios sont maintenant verifies: le local suffit (cout 0), le local echoue et on escalade en payant, le local est hors ligne et on bascule, et un runtime persistant recharge un etat accepte apres redemarrage. Une mission irroutable finit `FAIL` et `abandoned`, sans boucle.

## Dette ouverte a traiter

- PR `#1` (`robin/phase1-routing-policy-telemetry`) est **obsolete**: elle visait les memes ecarts depuis `f78f38d` et est desormais depassee par `main`. A fermer ou rebaser avant toute autre chose, sinon elle reintroduira des conflits.
- Le zip historique `nexus-ciel-complete.zip` et les deux PDF de specification restent a la racine. Une seule arborescence canonique: les deplacer dans `docs/` ou les retirer.
- `tests/test_phase0_acceptance.py` partage le `runtime` global de `nexus.api.app`, donc l'ordre des tests compte. A isoler par fixture quand la persistance arrivera completement.
- Le store PostgreSQL persiste pour l'instant un **snapshot unique** du runtime. C'est reversible et suffisant pour prouver la reprise, mais pas encore assez fin pour la memoire Phase 2 ni pour l'audit multi-missions a long terme.

## Prochaine etape concrete

1. Ajouter un test d'acceptation CI qui demarre PostgreSQL, applique Alembic, accepte une mission, recree le runtime et verifie la restauration depuis la base.
2. Rendre le smoke Compose reproductible (commande documentee + verification de volume persistant).
3. Ensuite seulement, attaquer le contrat Memory Core / SkillCard de la Phase 2.

## Roadmap restante

- Phase 3: Execution Fabric, Mission Guard, Validation Engine et rapports complets.
- Phase 4: Gymnase rejouable et Evolution Engine, 20 replays, +5%, veto regression, rollback.
- Phase 5: Capability Creation securise: oracle, second modele, sandbox niveau 3, probation, 10 succes.
- Phase 6: Great Sage conditionnel et Formal Reasoning deterministe.
- Phase 7: Redis Streams, OpenTelemetry, reprise sans perte et audit final.

## Regles de continuite

- Lire ce fichier avant toute modification.
- Une phase = code, tests d'acceptation, CI verte, checklist mise a jour, commit explicite.
- Verifier la **conclusion** du run CI, pas son existence: un run annule ne prouve rien.
- En CI rouge: corriger avant toute nouvelle phase.
- Une seule arborescence canonique; le zip historique reste une archive tant qu'il n'est pas retire par decision explicite.
- Aucun secret dans Git; aucune capacite generee ne peut ecrire dans `core/`.
- Ne jamais confondre prototype interne et production: interne n'autorise pas l'absence de garde-fous.
