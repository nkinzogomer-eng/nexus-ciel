# Journal de reprise Nexus Ciel

## Point d’arrêt
- Phase active: **Phase 0, fondations**
- Dernier commit: `feat: establish Phase 0 foundation with acceptance tests and CI`
- État: implémentation poussée sur `main`; CI GitHub doit maintenant exécuter les tests.

## Ce qui est livré
- Contrats Pydantic versionnés: Mission, Event, MissionState, Report, Capability.
- Event Bus asynchrone in-process.
- State Graph en mémoire avec état reprenable.
- Mission Journal append-only avec chaîne d’intégrité SHA-256.
- Capability Registry, toute nouvelle capacité en statut probationary.
- API FastAPI minimale: `/mission`, état, rapport, `/capabilities`, `/health`.
- Tests d’acceptation et workflow CI Python 3.12.

## Critère de sortie Phase 0
Une mission triviale doit être acceptée en 202, produire un rapport PASS, publier MissionAccepted et MissionValidated, et laisser un journal dont la chaîne est vérifiable.

## À vérifier avant Phase 1
1. La CI GitHub est verte.
2. Le workflow est reproductible avec `pip install -e '.[test]' && pytest`.
3. Aucun secret n’est présent dans le dépôt.
4. Le zip historique peut être archivé puis supprimé dans un commit séparé après validation humaine.

## Suite prévue
Phase 1: Router en cascade réel, cache Redis, au moins deux fournisseurs, health checks, journalisation des escalades et tests d’acceptation coût/qualité.

## Règle de continuité
Ne pas démarrer Phase 1 si la CI est rouge. Toute phase doit avoir: code suivi, tests d’acceptation, CI verte, README/journal de reprise mis à jour, puis commit identifiable.
