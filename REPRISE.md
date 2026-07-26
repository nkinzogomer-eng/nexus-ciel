# Journal de reprise Nexus Ciel

> Source de vérité. Une case n'est cochée que si le code et un test reproductible la justifient.

## Position actuelle

- Objectif: Nexus Ciel interne d'abord, auto-hébergé sur un hôte maîtrisé.
- Vision: Manas gelé, capacités et politiques probatoires et réversibles, apprentissage hors mission, cascade économique, validation en couches.
- Commit de référence main: `ca216b8`.
- Phase active: **Phase 2 ouverte, persistance d'abord.**
- PR #6: **scaffold Phase 2 validé par CI** sur `9aecfab`.
- CI PR #6: run `30214062985`, job `89825040897`, conclusion **success**, 50 tests, 19 secondes.
- Seul avertissement: dépréciation Node.js 20 des actions GitHub, sans impact sur Nexus Ciel.

## Phase 0 et Phase 1

- [x] Contrats Pydantic de base.
- [x] Event Bus in-process.
- [x] State Graph minimal.
- [x] Mission Journal chaîné et détection de falsification.
- [x] Capability Registry probatoire.
- [x] API branchée sur la cascade.
- [x] Router: politique read-only, cascade officielle, cache, télémétrie, escalade, erreurs bornées.
- [ ] Persistance réellement branchée au runtime.
- [ ] Reprise réelle après crash.
- [ ] Docker Compose vérifié avec restauration d'un état existant.

## Ce que PR #6 prouve

- Manifeste versionné couvrant `mission_states`, `mission_reports`, `mission_journal`, `capabilities` et `routing_telemetry`.
- Baseline Alembic et configuration PostgreSQL.
- Docker Compose avec PostgreSQL, volume persistant, migration avant démarrage API.
- Dockerfile reproductible.
- 50 tests CI verts pour verrouiller le scaffold et éviter de repartir de zéro.

## Ce que PR #6 ne prouve pas

Le scaffold ne persiste encore aucun état de mission: le runtime reste en mémoire et `resumable_after_crash` reste un problème ouvert dans le core gelé. Ne pas cocher la persistance sur cette seule base.

## Prochain jalon obligatoire: runtime durable

1. Ajouter un adaptateur persistant hors `nexus/core` pour State Graph, rapports, journal, capacités et télémétrie.
2. Faire écrire chaque mutation dans PostgreSQL avec transaction et idempotence.
3. Tester la reprise d'une mission terminée après recréation du runtime.
4. Tuer un processus pendant une mission, redémarrer, retrouver l'état `in_progress` et vérifier la chaîne du journal.
5. Définir une politique explicite pour les missions inachevées: reprise, abandon contrôlé ou reprise humaine.
6. Vérifier `docker compose up --build` et la restauration via `postgres_data`.
7. Seulement après ces preuves, fermer la persistance Phase 0 et commencer Memory Core.

## Phase 2b: Memory Core et SkillCards

À commencer uniquement après le jalon durable:

- [ ] Contrat Memory Core sans dupliquer les sources canoniques.
- [ ] SkillCard versionnée: contexte, méthode, pièges, coût, succès, provenance, hypothèse/confirmée.
- [ ] Adaptateur déterministe en test, pgvector ensuite.
- [ ] Seuil, fraîcheur, provenance, invalidation et contradictions.
- [ ] Brancher l'étage `memory` de la cascade.
- [ ] Belzébuth transforme succès et échecs en SkillCards.
- [ ] Confirmation après deux missions sources, jamais une seule.
- [ ] Mesurer une baisse d'itérations ou de coût par réutilisation.
- [ ] Prouver que Belzébuth ne modifie jamais le Capability Registry.

## Dette et risques connus

- Budget de mission déclaré mais pas encore bloquant: Mission Guard Phase 3.
- Providers encore simulés: gateway réel, timeouts, retries bornés, circuit breaker à construire.
- Cache en mémoire sans expiration et télémétrie non persistante.
- Création de capacités prévue en Phase 5, avec oracle, second modèle, sandbox niveau 3, probation et 10 succès.
- Zip historique et PDF de spécification encore à ranger dans une arborescence documentaire unique.

## Règles de continuité

- Lire ce fichier avant toute modification.
- Une phase = code, tests d'acceptation, exécution réelle, CI verte, checklist mise à jour, commit explicite.
- Une suite verte prouve les assertions écrites, pas le système entier: falsifier, débrancher, redémarrer et appeler la surface publique avant de fermer une phase.
- Aucun secret dans Git; aucune capacité gérée ne peut écrire dans `core/`.
- Ne jamais confondre prototype interne et production.
