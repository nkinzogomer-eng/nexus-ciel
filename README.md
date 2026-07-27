# Nexus Ciel

## Statut actuel

**Phase 1 close. Phase 2 en cours: persistance PostgreSQL branchée, gate kill/restart encore à valider sur main.** PR #3 a été fusionnée en squash dans `main`; PR #8 a été fermée comme doublon. La CI de validation des PR était verte avec seulement un warning Node.js 20 externe.

Voir [REPRISE.md](REPRISE.md) pour la source de vérité.

## Preuve obligatoire Phase 2

La gate démarre un sous-processus Nexus, accepte une mission, le tue par `SIGKILL`, recrée un runtime avec la même base PostgreSQL, puis exige la récupération de l'état, du rapport et de la chaîne du journal. Tant que cette gate et la restauration Compose ne sont pas vertes sur `main`, la persistance Phase 0 et la Phase 2 restent ouvertes.

## Route actuelle

`NEXUS_DATABASE_URL` active `build_runtime()` et le `PostgresSnapshotStore`; sans cette variable, Nexus reste explicitement en mémoire. Le store normalise `postgresql://` pour SQLAlchemy et `postgresql+psycopg://` pour psycopg.

## Prochaine étape

Valider la gate sur `main`, couvrir les missions interrompues, tester le volume Docker Compose, puis seulement construire Memory Core et SkillCards.
