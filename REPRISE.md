# Journal de reprise Nexus Ciel

> Source de vérité. Une case n'est cochée que si le code et un test reproductible la justifient.

## Position actuelle

- Objectif: Nexus Ciel interne d'abord, auto-hébergé sur un hôte maîtrisé.
- Vision: Manas gelé, capacités et politiques probatoires et réversibles, apprentissage hors mission, cascade économique, validation en couches.
- Commit de référence main: `ca216b8`.
- Phase active: **Phase 2 ouverte, persistance d'abord.**
- PR #6: scaffold vert, puis gate PostgreSQL kill/restart ajoutée.
- Dernier commit: `9f62416` (`fix: normalize SQLAlchemy PostgreSQL DSN for psycopg`).
- Dernière CI: run `30216128010`, job `89830540924`, **failure** le 27 juillet, après 28 secondes.

## État des preuves

- [x] Scaffold Phase 2: manifeste, baseline Alembic, Dockerfile, Compose, 50 tests, CI verte.
- [x] Adaptateur PostgreSQL hors `nexus/core` et branchement de `build_runtime()`.
- [x] Gate réelle ajoutée: sous-processus tué par `SIGKILL`, nouveau runtime, vérification état/rapport/journal.
- [ ] Gate kill/restart verte.
- [ ] Persistance Phase 0 validée.
- [ ] Docker Compose vérifié avec restauration d'un état existant.

## Ce que le dernier échec prouve

La CI historique du scaffold était verte, mais ne testait pas de persistance réelle. La nouvelle gate a donc correctement échoué après le câblage: il reste un défaut d'intégration à isoler dans le job, probablement dans la chaîne migration/connexion/écriture/lecture, mais aucune case ne doit être cochée sans un run vert.

Le runtime persistant cible maintenant les tables canoniques `mission_states`, `mission_reports`, `mission_journal` et `capabilities`. La télémétrie de routage n'est pas encore écrite dans PostgreSQL et reste ouverte.

## Prochaines actions obligatoires

1. Extraire l'erreur exacte de la gate PostgreSQL, pas deviner.
2. Corriger puis relancer la gate.
3. Vérifier que le processus meurt après commit, qu'un nouveau runtime lit le même `mission_id`, que le rapport existe et que `journal.verify_chain()` reste vrai.
4. Ajouter ensuite la mission interrompue `in_progress` et sa politique de reprise explicite.
5. Vérifier Compose avec volume persistent.
6. Seulement après: cocher la persistance Phase 0 et commencer Memory Core.

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
