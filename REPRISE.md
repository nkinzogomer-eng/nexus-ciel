# Journal de reprise Nexus Ciel

> Source de vérité. Une case n'est cochée que si le code et un test reproductible la justifient.

## Position actuelle

- Objectif: Nexus Ciel interne d'abord, auto-hébergé sur un hôte maîtrisé.
- Vision: Manas gelé, capacités et politiques probatoires et réversibles, apprentissage hors mission, cascade économique, validation en couches.
- Dernier commit main: `50d1da0` (squash de PR #3).
- Phase active: **Phase 2 ouverte, persistance PostgreSQL branchée mais gate kill/restart à valider sur main.**
- PR #3: fusionnée en squash.
- PR #8: fermée comme doublon, ses corrections DSN sont déjà intégrées.
- PR #6: scaffold historique vert, remplacé par la ligne persistante.

## CI et preuves

- PR #3: run `30220312697`, job `89841522174`, **success**, 48 secondes.
- PR #8: run `30224468531`, job `89852314957`, **success**, 40 secondes.
- Les deux runs ont seulement le warning externe Node.js 20, sans erreur Nexus.
- La gate PostgreSQL kill/restart a été ajoutée et le runtime persistant est câblé hors `nexus/core`; elle doit encore conclure verte sur `main` après fusion.

## Phase 0 et Phase 1

- [x] Contrats Pydantic de base.
- [x] Event Bus in-process.
- [x] State Graph minimal.
- [x] Mission Journal chaîné et détection de falsification.
- [x] Capability Registry probatoire.
- [x] API branchée sur la cascade.
- [x] Router: politique read-only, cascade officielle, cache, télémétrie, escalade, erreurs bornées.
- [ ] Persistance PostgreSQL/Alembic validée sur main.
- [ ] Reprise réelle après crash validée.
- [ ] Docker Compose vérifié avec restauration d'un état existant.

## Ce que le runtime persistant contient

- `build_runtime()` sélectionne le chemin PostgreSQL quand `NEXUS_DATABASE_URL` est fourni.
- `PostgresSnapshotStore` normalise les DSN SQLAlchemy et psycopg, lit et écrit les états, rapports, journal et capacités dans une transaction.
- `PersistentRuntime` recharge les sources canoniques après recréation du processus.
- La gate obligatoire démarre un sous-processus, accepte une mission, le tue par `SIGKILL`, redémarre un second processus et vérifie état, rapport et intégrité du journal.
- La télémétrie de routage et la politique de reprise des missions `in_progress` restent à finaliser.

## Prochaines actions obligatoires

1. Vérifier le run CI de `main` après la fusion et corriger toute régression.
2. Faire passer la gate PostgreSQL kill/restart sur main.
3. Ajouter la mission interrompue `in_progress` et décider reprise automatique, abandon contrôlé ou reprise humaine.
4. Vérifier Docker Compose avec volume persistant.
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
- Création de capacités prévue en Phase 5, avec oracle, second modèle, sandbox niveau 3, probation et 10 succès.
- Zip historique et PDF de spécification encore à ranger.

## Règles de continuité

- Lire ce fichier avant toute modification.
- Une phase = code, tests d'acceptation, exécution réelle, CI verte, checklist mise à jour, commit explicite.
- Une suite verte prouve les assertions écrites, pas le système entier: falsifier, débrancher, redémarrer et appeler la surface publique avant de fermer une phase.
- Aucun secret dans Git; aucune capacité gérée ne peut écrire dans `core/`.
- Ne jamais confondre prototype interne et production.
