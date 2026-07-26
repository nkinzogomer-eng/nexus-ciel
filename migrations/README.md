# Migrations Phase 2

Ce dossier contient la baseline Alembic de la persistance Phase 2.

Objectif: figer un point de depart unique pour PostgreSQL sans toucher `nexus/core`.
La preuve de reprise apres crash restera fermee tant que le runtime n'ecrit pas reellement dans ces tables.
