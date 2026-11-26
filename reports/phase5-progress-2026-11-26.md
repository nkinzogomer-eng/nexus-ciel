# Phase 5 — rapport de progression vérifiable

Date : 2026-11-26  
Branche : `feature/ciel-phase5-cognitive-operational-intelligence`  
Base inchangée : `51e297250d5af1648023bf05c90410af1b165390`

## Architecture livrée

La frontière `NaturalGoalInterpreter` accepte une demande textuelle de taille bornée et extrait uniquement des motifs explicites : objectif, résultat attendu, budget, durée, faits déclarés, hypothèses déclarées, inconnues, critères de vérification, risques et outils nécessitant une approbation. Elle renvoie `accepted` ou `needs_clarification`. Les ambiguïtés de cible pour une mutation workspace et les contradictions explicites bloquent ; une inconnue non bloquante ne déclenche pas de question. Le texte n’est pas présenté comme une compréhension générale du langage naturel.

Le résultat se convertit vers le `GoalUnderstanding` existant, puis suit sans doublon `MissionCompiler → StrategyEngine → CognitiveDecisionEngine → PlanEngine`. `CognitiveEngine.start_natural` refuse une ambiguïté bloquante au lieu de deviner. Le mode par défaut demeure `CORE_ONLY`.

`ApprovalLedger` persiste les demandes d’approbation sensibles, leur empreinte d’action, le contexte, l’expiration et la décision. `PersistentRuntime` restaure ce ledger avec les actions. `ActionExecutor` crée une demande pending avant une action sensible, puis n’exécute qu’après approbation persistante correspondant à l’empreinte exacte. Les permissions, budgets, limites, journal et recovery Phase 4.1 restent les autorités existantes.

## Preuves exécutées

- Tests ciblés Phase 5 : `8 passed`.
- Suite complète : `130 passed, 2 skipped` en `0.46s` (`132` tests au total) ; les deux skips exigent `NEXUS_DATABASE_URL` pour PostgreSQL live et le crash gate PostgreSQL.
- Compilation Python de `nexus`, `tests` et du script de démonstration : succès.
- Démonstrations réelles :
  - `reports/phase5-demos/nominal.json` : interprétation naturelle, stratégie `staged-verified`, calcul contrôlé et plan `succeeded`.
  - `reports/phase5-demos/failure_and_adaptation.json` : échec déterministe, décision `revise`, nouvelle version de plan, correction `calculate`, succès final.
  - `reports/phase5-demos/real_interruption.json` : processus enfant terminé par `SIGKILL` (`-9`), un seul appel handler, restauration `interrupted_uncertain`, replay idempotent sans second appel.

Commande de démonstration :

```text
PYTHONPATH=. /tmp/ciel-phase2-venv/bin/python scripts/phase5_demo_suite.py
```

## Limites restantes

La compréhension naturelle repose sur des motifs déterministes français/anglais et s’abstient hors de ce périmètre. Il n’existe pas d’UI d’approbation ni d’identité d’utilisateur fédérée ; l’approbateur est un identifiant applicatif validé non vide. Les outils opérationnels restent ceux de l’allowlist locale : calcul et workspace contrôlé ; aucun shell, navigateur, réseau libre ou sandbox de processus n’a été ajouté. L’observation indépendante repose sur des postconditions déterministes ou un oracle explicite, pas sur une compréhension sémantique générale.

La coordination multi-exécuteur reste limitée au processus et au registre partagés, et PostgreSQL demeure single-writer. Aucun système de mémoire apprenante, apprentissage long terme, auto-modification, intégration PRISM/Aetherion ou système multi-LLM n’a été ajouté.

La PR draft Phase 5 et le commit final restent à créer après la dernière validation.
