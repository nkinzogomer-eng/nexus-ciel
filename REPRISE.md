# Journal de reprise Nexus Ciel

> Source de vérité. Une case n'est cochée que si le code et un test reproductible la justifient.

## Position actuelle

- Objectif: Nexus Ciel interne d'abord, auto-hébergé sur un hôte maîtrisé.
- Vision: Manas gelé, capacités et politiques probatoires et réversibles, apprentissage hors mission, cascade économique, validation en couches.
- Dernier commit main: `551116e` (`Phase 2: abandon interrupted missions honestly after restart (#9)`), fusionné le 6 août 2026.
- Commit précédent: `078bbdd` (`docs: record Phase 2 PR merge and next persistence gate`).
- Phase active: **Phase 2 ouverte, persistance PostgreSQL branchée; la reprise automatique reste interdite et une mission interrompue est désormais requalifiée en abandon contrôlé au redémarrage.**
- PR #3: fusionnée en squash.
- PR #9: fusionnée en squash, apporte l'abandon contrôlé au redémarrage.
- PR #8: fermée comme doublon, ses corrections DSN sont déjà intégrées.
- PR #4 et #7: fermées comme remplacées, leur sujet (honnêteté de la reprise après crash) est couvert par PR #9.
- PR #5: fermée comme remplacée, son contrat de checkpointing est couvert par la ligne persistante de PR #3.
- PR #6: scaffold historique vert, remplacé par la ligne persistante, fermé.
- Aucune PR ouverte à ce jour.

## Politique de reprise après crash

Décision arrêtée, valable tant qu'aucune ré-exécution déterministe n'existe:

- Une mission persistée en `in_progress` retrouvée au redémarrage n'est **jamais** reprise automatiquement.
- Elle est requalifiée en `abandoned` de manière déterministe.
- Tout rapport `PASS` périmé est remplacé par un rapport `FAIL` d'interruption honnête.
- Une entrée `mission_interrupted` est ajoutée au Mission Journal.
- Motif: un runtime redémarré ne doit jamais laisser croire à une résumabilité qu'il n'a pas. Le verdict de récupération est explicite plutôt que silencieusement implicite.
- Les trois options envisagées étaient reprise automatique, abandon contrôlé et reprise humaine. L'abandon contrôlé est retenu; la reprise humaine reste ouverte pour une phase ultérieure.

## CI et preuves

- Commit `078bbdd`: checks **verts**. Workflow `CI on: push`, job `tests`, **success** le Sun Jul 27 en 37 secondes, avec le seul warning externe Node.js 20 déjà observé.
- PR #9: run `30800098628`, job `91642446683`, check `tests`, **success** le 3 août en 76 secondes, `mergeable_state: clean` avant fusion.
- PR #3: run `30220312697`, job `89841522174`, **success**, 48 secondes.
- PR #8: run `30224468531`, job `89852314957`, **success**, 40 secondes.
- Les runs observés n'ont pas d'erreur Nexus; seul le warning externe Node.js 20 persiste.
- Preuve apportée par PR #9: un snapshot relancé avec une mission `in_progress` la requalifie en `abandoned`, remplace tout rapport `PASS` éventuel par un `FAIL` honnête, et ajoute l'entrée de journal `mission_interrupted`. Régression couvrant l'écrasement d'un rapport de succès périmé incluse.
- **Non prouvé:** le run CI de `main` sur `551116e` n'a pas encore été observé jusqu'à sa conclusion. Il n'est pas compté comme vert tant qu'il n'a pas conclu.
- La gate PostgreSQL kill/restart et la restauration Compose doivent encore conclure vertes sur `main` avant fermeture de la phase.

## Phase 0 et Phase 1

- [x] Contrats Pydantic de base.
- [x] Event Bus in-process.
- [x] State Graph minimal.
- [x] Mission Journal chaîné et détection de falsification.
- [x] Capability Registry probatoire.
- [x] API branchée sur la cascade.
- [x] Router: politique read-only, cascade officielle, cache, télémétrie, escalade, erreurs bornées.
- [x] Mission interrompue détectée au redémarrage et requalifiée en abandon contrôlé.
- [ ] Persistance PostgreSQL/Alembic validée sur main.
- [ ] Reprise réelle après crash validée.
- [ ] Docker Compose vérifié avec restauration d'un état existant.

## Ce que le runtime persistant contient

- `build_runtime()` sélectionne le chemin PostgreSQL quand `NEXUS_DATABASE_URL` est fourni.
- `PostgresSnapshotStore` normalise les DSN SQLAlchemy et psycopg, lit et écrit les états, rapports, journal et capacités dans une transaction.
- `PersistentRuntime` recharge les sources canoniques après recréation du processus.
- Au redémarrage, toute mission laissée `in_progress` est requalifiée en `abandoned`, reçoit un rapport `FAIL` honnête, et journalise `mission_interrupted` tant qu'aucune reprise déterministe n'existe.
- La gate obligatoire démarre un sous-processus, accepte une mission, le tue par `SIGKILL`, redémarre un second processus et vérifie état, rapport et intégrité du journal.
- La télémétrie de routage persistante et la validation Compose restent à finaliser.

## Prochaines actions obligatoires

1. Observer le run CI de `main` sur `551116e` jusqu'à sa conclusion et corriger toute régression.
2. Faire passer la gate PostgreSQL kill/restart sur `main`.
3. Vérifier Docker Compose avec volume persistant et restauration d'un état existant.
4. Garder la politique de reprise en abandon contrôlé tant qu'aucune ré-exécution déterministe n'existe.
5. Cocher la persistance Phase 0 uniquement après ces preuves.
6. Ensuite seulement commencer Memory Core et SkillCards.

## Phase 2b: Memory Core et SkillCards

À commencer uniquement après le jalon durable:

- [ ] Contrat Memory Core sans dupliquer les sources canoniques.
- [ ] SkillCard versionnée: contexte, méthode, pièges, coût, succès, provenance, hypothèse/confirmée.
- [ ] Adaptateur déterministe en test, pgvector ensuite.
- [ ] Seuil, fraîcheur, provenance, invalidation et contradictions.
- [ ] Brancher l'étage `memory` de la cascade.
- [ ] Belzébuth transforme succès et échecs en SkillCards.
- [ ] Confirmation après deux missions sources, jamais une seule.
- [ ] Mesurer une baisse d'itérations ou de coût.
- [ ] Prouver que Belzébuth ne modifie jamais le Capability Registry.

## Dette et risques connus

- Budget de mission déclaré mais pas encore bloquant: Mission Guard Phase 3.
- Providers encore simulés: gateway réel, timeouts, retries bornés, circuit breaker à construire.
- Télémétrie encore volatile et non persistante.
- Cache en mémoire sans expiration.
- Reprise automatique absente par choix: politique actuelle = abandon contrôlé au redémarrage.
- Création de capacités prévue en Phase 5, avec oracle, second modèle, sandbox niveau 3, probation et 10 succès.
- Zip historique et PDF de spécification encore à ranger.

## Règles de continuité

- Lire ce fichier avant toute modification.
- Une phase = code, tests d'acceptation, exécution réelle, CI verte, checklist mise à jour, commit explicite.
- Une suite verte prouve les assertions écrites, pas le système entier: falsifier, débrancher, redémarrer et appeler la surface publique avant de fermer une phase.
- Aucun secret dans Git; aucune capacité gérée ne peut écrire dans `core/`.
- Ne jamais confondre prototype interne et production.
