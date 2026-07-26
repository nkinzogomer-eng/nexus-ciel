# Nexus Ciel

Nexus Ciel est un systeme d'orchestration et d'apprentissage **interne d'abord**: il recoit des missions, choisit une strategie economique, execute sous controle, valide les resultats et transforme l'experience en savoir-faire reutilisable.

## Statut actuel

**Phase 1 close et durcie (`12e1587`). Phase 2 ouverte, persistance d'abord.** Le Router respecte la cascade officielle, charge sa politique versionnee en lecture seule, contient les pannes de fournisseurs, trace chaque escalade et ne facture que ce qui est reellement depense. Le journal de mission detecte toute alteration de contenu. La Phase 0 reste incomplete sur la persistance: tout l'etat vit en memoire de processus tant qu'aucun store durable n'est configure.

Voir [REPRISE.md](REPRISE.md) pour l'etat detaille, la checklist cochable, les quatre defauts trouves en execution, la dette ouverte et la roadmap.

## Principes non negociables

- Manas/Core reste gele et modifiable par l'humain uniquement.
- Les sources canoniques restent uniques: State Graph, Mission Journal, Capability Registry.
- Les capacites et politiques evolutives sont versionnees, probatoires et reversibles.
- La validation deterministe precede le jugement LLM.
- Les budgets, retries, sandbox et kill-switch sont obligatoires avant autonomie accrue.
- L'apprentissage se fait en tache de fond, jamais au milieu d'une mission.

## Developpement local

```bash
pip install -e '.[test]'
pytest -q
```

46 tests d'acceptation Phase 1 et regressions. La CI GitHub execute les tests sur Python 3.12, puis rejoue les demos de succes et d'echec.

## Essayer en 10 secondes

```bash
python -m nexus.demo "resume le sprint"
python -m nexus.demo "probleme dur" --local-confidence 0.2
python -m nexus.demo "panne locale" --local-unavailable
python -m nexus.demo "impossible" --local-confidence 0.1 --secondary-confidence 0.2
```

La sortie donne le verdict, le cout reel, le cout evite par le cache, la trace d'escalade, la validite du journal et les evenements publies. Le dernier scenario sort en code 1 et laisse la mission en `abandoned`.

## API

```bash
uvicorn nexus.api.app:app --reload
```

`POST /mission` passe par la cascade et le store configure. `GET /mission/{id}` rend l'etat, `GET /mission/{id}/report` le rapport, `GET /policy` la politique en lecture seule, `GET /health` l'etat et l'integrite du journal.

## Persistance durable

Par defaut, l'API conserve encore un runtime en memoire. Configurez `NEXUS_RUNTIME_SNAPSHOT=/chemin/runtime.json` pour le store fichier deterministe, ou `NEXUS_DATABASE_URL=postgresql://nexus:nexus@db:5432/nexus_ciel` pour PostgreSQL. Le runtime persistant recharge etats, rapports, journal et capacites sans toucher a `core/`.

## Docker Compose

```bash
docker compose up --build
```

Compose demarre PostgreSQL, applique `alembic upgrade head`, puis sert l'API. La preuve PostgreSQL reelle et la restauration via volume restent necessaires avant de cocher completement la persistance de Phase 0.

## Politique et journal

La politique vit dans [`policies/routing_policy_v1.json`](policies/routing_policy_v1.json), propriete logique de l'Evolution Engine, et le Router ne peut pas l'ecrire. Chaque entree du journal est signee sur son contenu complet et chainee a la precedente; `verify_chain()` detecte les modifications de payload, acteur ou type.
