# Nexus Ciel

## Statut actuel

**Phase 1 close. Phase 2 persistance en cours, non validée.** Le scaffold PostgreSQL/Alembic/Compose a passé 50 tests, mais la nouvelle gate d'intégration kill/restart PostgreSQL a échoué après le câblage du runtime. C'est le bon comportement: la preuve a trouvé un défaut au lieu de laisser le décor PostgreSQL passer pour une persistance.

Voir [REPRISE.md](REPRISE.md) pour l'état exact.

## Preuve attendue

La gate démarre un sous-processus Nexus, accepte une mission, le tue par `SIGKILL`, recrée un runtime avec la même base PostgreSQL, puis exige la récupération de l'état, du rapport et de la chaîne du journal. Tant que ce test n'est pas vert, la persistance et la Phase 2 restent ouvertes.

## Règle de travail

Une CI verte du scaffold ne prouve pas le runtime. On ne ferme une phase qu'après exécution réelle, redémarrage, test d'intégrité et CI verte.
