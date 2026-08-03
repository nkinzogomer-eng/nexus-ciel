# Journal de reprise Nexus Ciel

> Source de vérité. Une case n'est cochée que si le code et un test reproductible la justifient.

## Position actuelle

- Objectif: Nexus Ciel interne d'abord, auto-hébergé sur un hôte maîtrisé.
- Vision: Manas gelé, capacités et politiques probatoires et réversibles, apprentissage hors mission, cascade économique, validation en couches.
- Dernier commit main: `078bbdd` (`docs: record Phase 2 PR merge and next persistence gate`).
- Phase active: **Phase 2 ouverte, persistance PostgreSQL branchée; la reprise automatique reste interdite et une mission interrompue est désormais requalifiée en abandon contrôlé au redémarrage.**
- PR #3: fusionnée en squash.
- PR #8: fermée comme doublon, ses corrections DSN sont déjà intégrées.
- PR #6: scaffold historique vert, remplacé par la ligne persistante.

## CI et preuves

- Commit `078bbdd`: état exact des checks non récupérable pendant ce réveil via les outils disponibles (pages GitHub Actions/checks illisibles), mais `main` n'a reçu aucun nouveau commit depuis le Mon Jul 27.
- PR #3: run `30220312697`, job `89841522174`, **success**, 48 secondes.
- PR #8: run `30224468531`, job `89852314957`, **success**, 40 secondes.
- Les deux runs ont seulement le warning externe Node.js 20, sans erreur Nexus.
- Preuve ajoutée sur cette branche: un snapshot relancé avec une mission `in_progress` la requalifie en `abandoned`, remplace tout rapport `PASS` éventuel par un `FAIL` honnête, et ajoute l'entrée de journal `mission_interrupted`.
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
- Au redémarrage, toute mission laissée `in_progress` est maintenant requalifiée en `abandoned`, reçoit un rapport `FAIL` honnête, et journalise `mission_interrupted` tant qu'aucune reprise déterministe n'existe.
- La gate obligatoire démarre un sous-processus, accepte une mission, le tue par `SIGKILL`, redémarre un second processus et vérifie état, rapport et intégrité du journal.
- La télémétrie de routage persistante et la validation Compose restent à finaliser.

## Prochaines actions obligatoires

1. Retrouver une preuve exploitable du run CI exact de `078bbdd` ou observer le prochain run `main` avec ses checks.
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
