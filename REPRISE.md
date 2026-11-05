# Journal de reprise Nexus Ciel

> Source de vérité. Une case n'est cochée que si le code et un test reproductible la justifient.

## Position actuelle

- Objectif: Nexus Ciel interne d'abord, auto-hébergé sur un hôte maîtrisé.
- Vision: Manas gelé, capacités et politiques probatoires et réversibles, apprentissage hors mission, cascade économique, validation en couches.
- Base actuelle de `main` pour la branche de finalisation: `3d8cf71b42ec9b3260768c5c454808bb450a153d` (journal de recherche CIEL, 19 août 2026).
- Commit précédent: `078bbdd` (`docs: record Phase 2 PR merge and next persistence gate`).
- Phase active: **Phase 2 ouverte, persistance PostgreSQL branchée; la reprise automatique reste interdite et une mission interrompue est désormais requalifiée en abandon contrôlé au redémarrage.**
- PR #3: fusionnée en squash.
- PR #9: fusionnée en squash, apporte l'abandon contrôlé au redémarrage.
- PR #8: fermée comme doublon, ses corrections DSN sont déjà intégrées.
- PR #4 et #7: fermées comme remplacées, leur sujet (honnêteté de la reprise après crash) est couvert par PR #9.
- PR #5: fermée comme remplacée, son contrat de checkpointing est couvert par la ligne persistante de PR #3.
- PR #6: scaffold historique vert, remplacé par la ligne persistante, fermé.
- PR #10 ouverte en brouillon sur `work/ciel-finalization-2026-11-05`; elle n'est pas fusionnée.

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
- La télémétrie de routage persistante reste à finaliser. La validation Compose est passée sur le candidat de persistance.

## Preuves de validation sur la branche de finalisation (5 novembre 2026)

La branche `work/ciel-finalization-2026-11-05`, proposée dans la PR #10, a passé la CI GitHub Actions sur le commit `4b57e79f0f8c2bcb2a73bb8eafd81675a11504b4`.

- Run CI: [42016899505](https://github.com/nkinzogomer-eng/nexus-ciel/actions/runs/42016899505), conclusion `success`.
- 59 tests pytest passés en 1,58 s; aucun test ignoré dans cette exécution.
- `test_postgres_sigkill_gate_recovers_and_abandons_mission`: PASS avec le service PostgreSQL réel de la CI.
- Gate Docker Compose: PASS; mission `validated` et rapport `PASS` conservés après `compose down` puis `compose up`, chaîne du Mission Journal valide.
- Migrations PostgreSQL, smoke run et test du chemin non routable: PASS.

**Portée exacte:** ces preuves valident le candidat de Phase 2 sur la branche et la PR #10. Elles ne signifient pas que `main` a déjà reçu ces changements. La Phase 2 ne sera fermée qu'après intégration contrôlée et vérification du commit résultant sur `main`. Aucun merge n'est effectué par cette mise à jour.

## Prochaines actions obligatoires

1. Observer le run CI de `main` sur `551116e` jusqu'à sa conclusion et corriger toute régression.
2. Faire passer la gate PostgreSQL kill/restart sur `main`.
3. Vérifier Docker Compose avec volume persistant et restauration d'un état existant.
4. Garder la politique de reprise en abandon contrôlé tant qu'aucune ré-exécution déterministe n'existe.
5. Cocher la persistance Phase 0 uniquement après ces preuves.
6. Ensuite seulement commencer Memory Core et SkillCards.

## Finalisation CIEL — travail additionnel (5 novembre 2026)

Les éléments suivants ont été ajoutés sur la branche de finalisation après le candidat de persistance:

- `DeterministicOutputVerifier`: modes `contains_all`, `contains_any`, `exact_match`, `json_valid` et `non_empty`. Une réponse de modèle seule ne peut plus produire un `PASS`; sans oracle pris en charge, le résultat est `PARTIAL`.
- Les rapports conservent le texte généré pour que l'utilisateur puisse examiner le résultat.
- `MissionGuard` valide les budgets; le routeur pré-évalue les fournisseurs, contrôle les coûts réels et cumule les dépenses sur les escalades.
- `OpenAICompatibleProvider` réalise un appel HTTP réel vers `/chat/completions`, avec timeout, usage tokens et estimation/coût calculé. Les prix hébergés doivent être explicitement configurés.
- L'API de production n'active plus silencieusement les fournisseurs synthétiques. Ceux-ci sont réservés à `NEXUS_TEST_MODE` dans les tests.
- `.env.example` et README actualisés.

**Limites restantes:** l'oracle est volontairement simple et ne prouve pas la sémantique d'une mission complexe; un seul profil de fournisseur réel est configuré; aucun moteur d'outils, planificateur multi-étapes, boucle de mission longue, Memory Core, SkillCards, circuit breaker, télémétrie persistante ou interface Telegram complète n'est encore validé.

**Preuves:** run `42049088295`: 65 tests passés et gate Compose verte sur un commit intermédiaire. Le cumul budgétaire, l'adaptateur réel et les tests associés ont été ajoutés ensuite; un nouveau run CI sur la tête actuelle est obligatoire avant de déclarer ces changements validés.

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

- Mission Guard de budget implémenté sur la branche: préflight, coût réel et budget cumulatif d'escalade; CI du dernier commit encore requise.
- Adaptateur OpenAI-compatible réel implémenté sur la branche; configuration explicite par variables d'environnement. Timeouts présents, mais retries bornés, circuit breaker et profils multi-fournisseurs restent à construire.
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
