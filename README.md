# Nexus Ciel

## Statut actuel

**Phase 1 close. Phase 2: les gates PostgreSQL SIGKILL et restauration Docker Compose passent sur la branche de finalisation; intégration et revalidation sur `main` encore nécessaires.**

Base actuelle de `main` pour cette branche: `3d8cf71b42ec9b3260768c5c454808bb450a153d` (19 août 2026). PR #3 et PR #9 sont fusionnées en squash. PR #4, #5, #6, #7 et #8 fermées comme doublons ou remplacées par la ligne persistante. Aucune PR ouverte.

La CI de la PR #10 est verte sur le candidat de finalisation: 59 tests passés, gate PostgreSQL SIGKILL réussie et restauration Compose validée. Cela ne constitue pas encore une validation de `main`; aucun merge n'a été effectué.

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
