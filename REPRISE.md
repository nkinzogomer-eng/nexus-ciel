# Journal de reprise Nexus Ciel

> Source de vérité pour reprendre le projet. Une case n'est cochée que si le code et un test reproductible la justifient.

## Position actuelle

- Objectif: Nexus Ciel **interne d'abord**, auto-hébergé sur un hôte maîtrisé.
- Vision: Manas gelé, capacités/politiques probatoires et réversibles, apprentissage hors mission, cascade économique, validation en couches.
- Dernier commit: `086ad85` (`feat: close Phase 1 routing contracts, policy, telemetry, and acceptance coverage`).
- Phase active: **Phase 1, validation CI puis transfert vers Phase 2**.
- CI: attendre le run GitHub correspondant exactement à `086ad85`. Ne pas cocher la validation finale avant un run vert.

## Phase 0

- [x] Contrats Pydantic de base.
- [x] Event Bus in-process.
- [x] State Graph minimal.
- [x] Mission Journal append-only chaîné.
- [x] Capability Registry probatoire.
- [x] API minimale et rapport PASS.
- [ ] Persistance PostgreSQL/Alembic et reprise après crash réelle.
- [ ] Docker Compose reproductible.

## Phase 1: routage économique

### Livré dans `086ad85`

- [x] Contrat fournisseur: `complete`, `health`, `cost_estimate`, `capabilities`.
- [x] Cascade officielle déclarée: cache, mémoire, formel, outil, petit modèle, grand modèle, profond.
- [x] Politique versionnée en lecture seule pour le Router, propriétaire logique `evolution_engine`.
- [x] Cache, health checks et escalade avec justification.
- [x] Échec borné et explicable quand aucun fournisseur n'est suffisant.
- [x] Tests d'acceptation de coût minimal, escalade, indisponibilité, cache, contrat et échec.

### À vérifier avant clôture

- [ ] CI verte pour le commit `086ad85`.
- [ ] Vérification manuelle que le fichier de politique reste une donnée versionnée et que le Router ne l'écrit pas.
- [ ] Ajouter plus tard la télémétrie persistante par appel: latence, tokens, coût, succès/échec.
- [ ] Remplacer les fournisseurs simulés par Ollama/New-API derrière un AI Gateway réel.
- [ ] Ajouter Redis quand la persistance de Phase 0 est en place.

### Critère PASS Phase 1

Le Router choisit le niveau le moins coûteux suffisant, trace chaque escalade, ignore les fournisseurs indisponibles, échoue sans boucle si aucun résultat n'atteint le seuil, et respecte la cascade officielle.

## Prochaine étape: Phase 2

Ne commencer qu'après CI verte sur `086ad85`.

- [ ] Concevoir le contrat Memory Core sans dupliquer les sources canoniques.
- [ ] Ajouter SkillCard versionnée: contexte, méthode, pièges, coût, taux de réussite, provenance, statut hypothèse/confirmée.
- [ ] Implémenter d'abord un adaptateur mémoire déterministe en test, puis pgvector.
- [ ] Ajouter seuil strict, fraîcheur, provenance, invalidation et gestion des souvenirs contradictoires.
- [ ] Implémenter Belzébuth pour transformer les missions terminées en SkillCards, réussites et échecs.
- [ ] Confirmer une SkillCard après deux missions sources, jamais après une seule.
- [ ] Ajouter un test de réutilisation mesurant une baisse d'itérations ou de coût.
- [ ] Ajouter un test prouvant que Belzébuth ne modifie jamais le Capability Registry.

## Roadmap restante

- Phase 3: Execution Fabric, Mission Guard, Validation Engine et rapports complets.
- Phase 4: Gymnase rejouable et Evolution Engine, 20 replays, +5%, veto régression, rollback.
- Phase 5: Capability Creation sécurisé: oracle, second modèle, sandbox niveau 3, probation, 10 succès.
- Phase 6: Great Sage conditionnel et Formal Reasoning déterministe.
- Phase 7: Redis Streams, OpenTelemetry, reprise sans perte et audit final.

## Règles de continuité

- Lire ce fichier avant toute modification.
- Une phase = code, tests d'acceptation, CI verte, checklist mise à jour, commit explicite.
- En CI rouge: corriger avant toute nouvelle phase.
- En CI en cours: ne rien modifier.
- Une seule arborescence canonique; le zip historique reste une archive tant qu'il n'est pas retiré par décision explicite.
- Aucun secret dans Git; aucune capacité générée ne peut écrire dans `core/`.
- Ne jamais confondre prototype interne et production: interne n'autorise pas l'absence de garde-fous.
