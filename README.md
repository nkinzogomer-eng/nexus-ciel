# Nexus Ciel

## Statut actuel

**Phase 1 close. Phase 2 en cours: persistance PostgreSQL branchée, gate kill/restart encore à valider sur `main`.**

Dernier commit `main`: `551116e` (squash de PR #9, 6 août 2026). PR #3 et PR #9 fusionnées en squash. PR #4, #5, #6, #7 et #8 fermées comme doublons ou remplacées par la ligne persistante. Aucune PR ouverte.

La CI de validation des PR était verte, avec seulement un warning Node.js 20 externe. Le run CI de `main` sur `551116e` n'a pas encore été observé jusqu'à sa conclusion et n'est donc **pas** compté comme vert.

Voir [REPRISE.md](REPRISE.md) pour la source de vérité.

## Politique de reprise après crash

Une mission persistée en `in_progress` retrouvée au redémarrage n'est **jamais** reprise automatiquement. Elle est requalifiée en `abandoned` de façon déterministe, tout rapport `PASS` périmé est remplacé par un `FAIL` d'interruption honnête, et une entrée `mission_interrupted` est ajoutée au Mission Journal.

Un runtime redémarré ne doit jamais laisser croire à une résumabilité qu'il n'a pas. La reprise humaine reste une option ouverte pour une phase ultérieure.

## Preuve obligatoire Phase 2

La gate démarre un sous-processus Nexus, accepte une mission, le tue par `SIGKILL`, recrée un runtime avec la même base PostgreSQL, puis exige la récupération de l'état, du rapport et de la chaîne du journal. Tant que cette gate et la restauration Compose ne sont pas vertes sur `main`, la persistance Phase 0 et la Phase 2 restent ouvertes.

## Route actuelle

`NEXUS_DATABASE_URL` active `build_runtime()` et le `PostgresSnapshotStore`; sans cette variable, Nexus reste explicitement en mémoire. Le store normalise `postgresql://` pour SQLAlchemy et `postgresql+psycopg://` pour psycopg.

## Prochaine étape

Confirmer le run CI de `main`, faire passer la gate kill/restart, tester la restauration du volume Docker Compose, puis seulement construire Memory Core et SkillCards.
