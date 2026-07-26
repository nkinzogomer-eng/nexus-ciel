# Nexus Ciel

Nexus Ciel est un système d'orchestration et d'apprentissage **interne d'abord**: il reçoit des missions, choisit une stratégie économique, exécute sous contrôle, valide les résultats et transforme l'expérience en savoir-faire réutilisable.

## Statut actuel

**Phase 1 close et durcie. Phase 2 ouverte, scaffold de persistance validé.** La PR #6 est passée au vert avec 50 tests. Elle pose le manifeste de schéma, Alembic, PostgreSQL, Docker Compose et les garde-fous documentaires, mais ne prétend pas encore fournir la reprise après crash.

Voir [REPRISE.md](REPRISE.md) pour la checklist exacte et le prochain jalon.

## Principes

- Manas/Core reste gelé et modifiable par l'humain uniquement.
- Les sources canoniques restent uniques: State Graph, Mission Journal, Capability Registry.
- Les capacités et politiques évolutives sont versionnées, probatoires et réversibles.
- La validation déterministe précède le jugement LLM.
- Budgets, retries, sandbox et kill-switch sont obligatoires avant autonomie accrue.
- L'apprentissage se fait hors mission.

## Développement local

```bash
pip install -e '.[test]'
pytest -q
```

La CI PR #6 est verte: 50 tests, puis vérifications de migration et de Compose. L'avertissement Node.js 20 vient des actions GitHub et n'est pas une erreur du projet.

## Essayer le Router

```bash
python -m nexus.demo "resume le sprint"
python -m nexus.demo "probleme dur" --local-confidence 0.2
python -m nexus.demo "panne locale" --local-unavailable
python -m nexus.demo "impossible" --local-confidence 0.1 --secondary-confidence 0.2
```

## API

```bash
uvicorn nexus.api.app:app --reload
```

`POST /mission` passe par la cascade. `GET /mission/{id}` rend l'état, `/report` le rapport, `/policy` la politique read-only et `/health` l'intégrité du journal.

## Persistance Phase 2

```bash
pip install -e '.[postgres]'
docker compose up --build
```

Le scaffold contient `nexus/persistence/manifest.py`, une baseline Alembic et un Compose PostgreSQL + API avec volume `postgres_data`. La prochaine étape est le câblage réel du runtime, puis une preuve kill/restart. Tant que cette preuve n'existe pas, l'état reste considéré comme volatil.

## Journal de mission

Chaque entrée est signée sur son contenu complet et chaînée à la précédente. `verify_chain()` détecte les modifications de payload, d'acteur ou de type, et `tampered_entries()` les localise.

## Roadmap

Persistance durable, puis Memory Core et SkillCards, ensuite Execution Fabric et Mission Guard, Gymnase et Evolution Engine, création sécurisée de capacités, raisonnement formel et observabilité durable. La création de capacités est prévue en Phase 5, pas encore implémentée.
