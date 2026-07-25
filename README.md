# Nexus Ciel

Nexus Ciel est un système d'orchestration et d'apprentissage **interne d'abord**: il reçoit des missions, choisit une stratégie économique, exécute sous contrôle, valide les résultats et transforme l'expérience en savoir-faire réutilisable.

## Statut actuel

**Prototype Phase 1, validation CI en attente.** La Phase 0 minimale est livrée; le Router Phase 1 existe, mais sa conformité complète aux contrats V2.5.2/V3 reste à fermer avant Phase 2.

Voir [REPRISE.md](REPRISE.md) pour l'état détaillé, la checklist cochable, les écarts documentaires et la roadmap.

## Principes non négociables

- Manas/Core reste gelé et modifiable par l'humain uniquement.
- Les sources canoniques restent uniques: State Graph, Mission Journal, Capability Registry.
- Les capacités et politiques évolutives sont versionnées, probatoires et réversibles.
- La validation déterministe précède le jugement LLM.
- Les budgets, retries, sandbox et kill-switch sont obligatoires avant autonomie accrue.
- L'apprentissage se fait en tâche de fond, jamais au milieu d'une mission.

## Développement local

```bash
pip install -e '.[test]'
pytest -q
```

La CI GitHub exécute les mêmes tests sur Python 3.12.
