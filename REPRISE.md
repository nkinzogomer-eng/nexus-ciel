# Journal de reprise Nexus Ciel

> Document de continuité pour toute personne qui reprend le dépôt. Les cases cochées sont des faits vérifiés par un commit et/ou une CI verte. Ne jamais considérer une phase comme terminée sur la seule présence du code.

## Position actuelle

- Objectif: Nexus Ciel **interne d'abord**, auto-hébergé sur un hôte maîtrisé. Pas de distribution publique ni de multi-tenant dans cette roadmap.
- Vision conservée: noyau Manas gelé, capacités/politiques évolutives mais probatoires, apprentissage en arrière-plan, économie par cascade, validation en couches.
- Dernier commit: `40131e9` (`ci: make validation reproducible and observable for every phase`).
- CI: seul le run du commit Phase 0 `e1aba88` est actuellement observé vert. Les commits Phase 1 et `40131e9` restent **NON VALIDÉS par CI**.
- Phase active: **Phase 1, fermeture de conformité et validation**.

## Ce qui est réellement livré

- [x] Contrats Pydantic de base: Mission, Event, MissionState, Report, Capability.
- [x] Event Bus asynchrone in-process.
- [x] State Graph en mémoire.
- [x] Mission Journal en mémoire, append-only logique et chaîné par hash.
- [x] Capability Registry en mémoire, statut initial probationary.
- [x] API minimale: `/mission`, état, rapport, `/capabilities`, `/health`.
- [x] Router prototype: cache mémoire, health checks, deux fournisseurs abstraits, seuil de confiance et escalade.
- [x] Tests d'acceptation de base et workflow CI Python 3.12.
- [ ] Persistance réelle: PostgreSQL, pgvector, Redis, migrations Alembic.
- [ ] Déploiement Docker Compose reproductible.
- [ ] Mission Guard et Validation Engine complets.
- [ ] AI Gateway distinct du Router et contrat fournisseur complet.
- [ ] Observabilité, Cost Monitor et rapports d'évolution/coûts.
- [ ] Memory Core, Belzébuth, Gymnase, Evolution, Capability Creation et Great Sage.

## Blocage immédiat: fermeture Phase 1

- [ ] Vérifier qu'un run CI est créé pour le dernier commit `40131e9`.
- [ ] Si la CI échoue: lire le log, corriger la cause, pousser un commit correctif et relancer.
- [ ] Ajouter un test de contrat ProviderAdapter: `complete`, `health`, estimation de coût et capacités.
- [ ] Remplacer les noms d'étages simplifiés par la cascade officielle: cache, mémoire, formel, outil, petit modèle, grand modèle, profond.
- [ ] Introduire une politique de routage versionnée en lecture seule pour le Router.
- [ ] Ajouter télémétrie structurée par appel: fournisseur, étage, coût, latence, tokens, succès/échec.
- [ ] Ajouter un test négatif: aucun fournisseur suffisant doit produire un échec borné et explicable.
- [ ] Définition de sortie: CI verte sur le dernier commit + tests d'acceptation Phase 1 verts + checklist ci-dessus cochée.

## Ce qui manque vraiment, par priorité

### Bloquant architectural
1. Sources de vérité persistantes et reprise après crash réelle.
2. Séparation stricte Core immuable / données évolutives / capacités probatoires.
3. Validation déterministe avant tout jugement LLM.
4. Budgets et kill-switch effectifs, pas seulement déclarés.
5. Tests de sécurité de sandbox avant toute création/exécution de code.

### Important mais non bloquant pour le prototype interne
- Redis Streams, OpenTelemetry, dashboards temps réel, Kubernetes, microVM, Neo4j et multi-tenant. Ces éléments restent reportés conformément à V3.
- Ne pas courir après chaque nouveau modèle: Nexus doit rester compétitif par son routage, sa mémoire, ses outils, ses preuves et son coût total, pas par une dépendance à un modèle précis.

## Roadmap de construction alignée V2.5.2/V3

### Phase 0: fondations vivantes
État: **partiellement validée**. La CI du commit `e1aba88` est verte, mais la persistance complète exigée par la documentation manque.

- [x] Contrats partagés et API triviale.
- [x] Event Bus, State Graph, Journal, Registry en version minimale.
- [x] Mission triviale produisant un rapport PASS.
- [ ] PostgreSQL + Alembic + reprise après crash prouvée.
- [ ] Une seule arborescence canonique, sans dépendre du zip historique.

Amélioration recommandée: ajouter un test de redémarrage qui recharge une mission inachevée depuis PostgreSQL et vérifie l'intégrité du Journal.

### Phase 1: économie et routage
État: **prototype livré, validation CI manquante**.

- [x] Cache et escalade de base.
- [x] Health checks et deux fournisseurs abstraits.
- [ ] Cascade officielle à 7 niveaux.
- [ ] Politique versionnée modifiable uniquement par Evolution Engine.
- [ ] AI Gateway avec retries bornés, fallback, circuit breaker et télémétrie.
- [ ] Redis pour cache sémantique interne.

Amélioration recommandée: tester le Router avec missions normales et critiques, en vérifiant coût, latence, disponibilité, justification de chaque escalade et exclusion de GPT4Free des chemins critiques.

### Phase 2: Memory Core + Belzébuth
État: **à construire après validation Phase 1**.

- [ ] Indexation pgvector sans dupliquer les sources canoniques.
- [ ] Récupération avec seuil strict, fraîcheur, provenance et invalidation.
- [ ] Belzébuth produit des SkillCards structurées pour réussites et échecs.
- [ ] Hypothèse après une mission, confirmation après deux missions.
- [ ] Test mesurant moins d'itérations ou de coût sur une mission similaire.

Amélioration recommandée: inclure des tests de souvenirs contradictoires et prouver qu'un souvenir proche mais faux n'est jamais accepté sans validation.

### Phase 3: Execution Fabric + Guard + Validation
État: **à construire**.

- [ ] Trois niveaux d'isolation, budgets CPU/mémoire/temps, retries bornés.
- [ ] Mission Guard pendant l'exécution: budget, périmètre, actions interdites, kill-switch.
- [ ] Validation Engine après production: déterministe, LLM si nécessaire, juge fournisseur différent si critique.
- [ ] Rapports PASS/FAIL/PARTIAL complets.

Amélioration recommandée: tests d'attaque et de dépassement de budget, avec preuve qu'une action interdite est coupée avant son effet irréversible.

### Phase 4: Gymnase + Evolution Engine
État: **à construire**.

- [ ] Missions de référence rejouables.
- [ ] Évolution hors ligne, par lots, jamais pendant une mission.
- [ ] Promotion seulement après au moins 20 replays, +5% minimum, sans régression.
- [ ] Rollback et comparaison permanente à la politique par défaut.

Amélioration recommandée: tests de veto automatique sur une régression d'une seule mission critique.

### Phase 5: Capability Creation Engine
État: **à construire**.

- [ ] Oracle réel défini avant génération.
- [ ] Revue par un modèle distinct ou Formal Reasoning.
- [ ] Sandbox niveau 3 sans réseau, FS temporaire, rollback total.
- [ ] Probation puis promotion après 10 succès réels par défaut.
- [ ] Échec répété borné, sans boucle infinie.

Amélioration recommandée: rendre impossible techniquement toute écriture de `core/` depuis une capacité générée, et tester ce refus.

### Phase 6: Great Sage + Formal Reasoning
État: **à construire**.

- [ ] Score de criticité normalisé et seuil configurable.
- [ ] Great Sage réveillé seulement pour les décisions critiques.
- [ ] Mémoire, critique, simulation et stratégie séparées.
- [ ] Raisonnement formel déterministe au niveau 3, distinct du raisonnement profond niveau 7.

Amélioration recommandée: tests reproductibles sur contraintes logiques et tests prouvant que Great Sage ne se déclenche pas sur une mission banale.

### Phase 7: durcissement interne
État: **à construire en dernier**.

- [ ] Redis Streams derrière le même Protocol EventBus.
- [ ] OpenTelemetry bout-en-bout.
- [ ] Revue des quatre surfaces: noyau, mémoire, capacités, fournisseurs/secrets.
- [ ] Redémarrage sans perte d'événements et rapports d'audit.

Amélioration recommandée: scénario de panne contrôlée avec reprise, déduplication d'événements et vérification de la chaîne d'audit.

## Règles de continuité pour les développeurs

- Une phase n'est terminée que si son critère PASS est automatisé, la CI est verte et ce fichier est mis à jour.
- Toute décision nouvelle doit être ajoutée dans un ADR avant le code.
- Toute capacité ou politique nouvelle naît probatoire et reste réversible.
- Aucun secret, code généré ou modification de `core/` ne passe hors des frontières prévues.
- Chaque commit doit dire ce qu'il apporte; éviter les commits mélangeant refactor, feature et suppression.
- Avant de continuer: lire ce journal, vérifier le dernier commit et lancer les tests.
