# Journal de reprise Nexus Ciel

> Source de verite pour reprendre le projet. Une case n'est cochee que si le code et un test reproductible la justifient.

## Position actuelle

- Objectif: Nexus Ciel **interne d'abord**, auto-heberge sur un hote maitrise.
- Vision: Manas gele, capacites/politiques probatoires et reversibles, apprentissage hors mission, cascade economique, validation en couches.
- Dernier commit de durcissement main: `12e1587`.
- Phase active: **Phase 1 close et durcie. Phase 2 ouverte, persistance d'abord.**
- PR #1 fermee comme obsolete. PR #2 est en cours de resolution sur le main durci.

## Phase 0 et Phase 1

- [x] Contrats Pydantic de base.
- [x] Event Bus in-process.
- [x] State Graph minimal.
- [x] Mission Journal chainee et detection de falsification.
- [x] Capability Registry probatoire.
- [x] API branchee sur le Router, et non sur le bouchon Phase 0.
- [x] Router Phase 1: politique versionnee read-only, cascade officielle, classement par rang/cout, cache, telemetrie, escalade et echec borne.
- [x] Resilience fournisseur: health/complete en erreur sont contenus, traces et escalades.
- [ ] Persistance PostgreSQL/Alembic et reprise apres crash reelle.
- [ ] Docker Compose reproductible avec preuve de restauration.

La partie centrale Phase 0-1 est fonctionnelle pour un prototype interne: mission, etat, journal, bus, registre, API, routeur et demo ont tous un chemin execute de bout en bout. Elle n'est pas complete au sens production: etat volatile par defaut, budget non applique, providers simules, cache sans expiration et telemetrie non persistante.

## Ce que les tests prouvent aujourd'hui

- 46 tests locaux de Phase 1 et regressions passent dans l'environnement de validation disponible.
- Scenarios verifies: local suffit, escalade payante, fournisseur hors ligne, fournisseur qui leve, cache gratuit, journal falsifie, API routee, mission irroutable sans boucle.
- La CI GitHub reste l'autorite finale pour les dependances reelles et doit rendre un run concluant sur le commit fusionne.

## Phase 2: persistance d'abord, non validee

La PR #2 pose les fondations suivantes, mais ne ferme pas encore la phase:

- Store fichier deterministe avec reprise d'etat, rapports, journal et capacites.
- Store PostgreSQL JSONB, migration Alembic, factory de runtime et Docker Compose.
- `resumable_after_crash=False` en ephemere, `True` uniquement sur runtime persistant.
- Tests de reprise apres restart fichier, y compris mission restee `in_progress` apres crash simule.

Reste obligatoire avant validation:

- [ ] Test CI sur PostgreSQL reel avec migration appliquee et restauration apres recreation du runtime.
- [ ] Smoke Compose reproductible avec verification du volume persistant.
- [ ] Reprise explicite des missions inachevees: rejouer, abandonner ou reprendre sous politique, jamais seulement les exposer.
- [ ] Verifier que le snapshot JSONB est suffisant avant d'engager la Memory Core.

## Ensuite: Memory Core

Seulement apres la persistance validee:

- [ ] Contrat Memory Core sans dupliquer les sources canoniques.
- [ ] SkillCard versionnee avec contexte, methode, pieges, cout, succes, provenance et statut.
- [ ] Adaptateur deterministe d'abord, pgvector ensuite.
- [ ] Seuil, fraicheur, provenance, invalidation et contradictions.
- [ ] Brancher l'etage `memory` de la cascade.
- [ ] Belzebuth transforme succes et echecs en SkillCards.
- [ ] Confirmation apres deux missions sources, jamais une seule.
- [ ] Test de reutilisation mesurant baisse d'iterations ou de cout.
- [ ] Test prouvant que Belzebuth ne modifie jamais le Capability Registry.

## Jugement d'architecture

Nexus Ciel est aujourd'hui un prototype d'orchestration interne avec des garde-fous serieux, pas une entite autonome complete. Les contrats, limites, validation et reversibilite existent en partie; l'execution reelle multi-outils, la memoire, la persistence PostgreSQL prouvee, les budgets, sandbox, kill-switch, gateway avec timeouts/retries/circuit breaker, et l'apprentissage ferme manquent encore.

Il est donc **prometteur et avance pour un prototype interne**, mais pas au niveau d'une entite autonome complete de son epoque. Oui, l'architecture peut etre construite entierement, mais seulement par phases avec preuves, et pas en sautant la persistance ou les garde-fous.

## Regle de continuite

Une suite verte prouve les assertions ecrites, pas le systeme entier. A chaque phase: code, tests d'acceptation, execution reelle, CI verte, checklist mise a jour, commit explicite. Aucun secret dans Git; aucune capacite generee ne peut ecrire dans `core/`.
