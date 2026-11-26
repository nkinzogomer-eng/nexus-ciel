# CIEL Phase 4.1 — Audit initial

Date : 2026-11-25  
Branche : `hardening/ciel-phase4-1-reliability-recovery`  
Base exacte : `64466f8baec41c2a23c09f4779dfe98b4c924322`  
Dépôt : `https://github.com/nkinzogomer-eng/nexus-ciel`

## Périmètre et méthode

L’audit porte sur les composants déjà livrés : `ActionRequest`, `ActionRecord`, `ActionExecutor`, `ToolRegistry`, `PersistentRuntime`, le journal chaîné, `CognitiveEngine.execute_action()` et le store PostgreSQL. Aucun moteur n’est reconstruit. Les reproductions ci-dessous ont été exécutées sur le commit de base, avec Python 3.12 et l’environnement `/tmp/ciel-phase2-venv`.

## Reproductions P0

### P0-A — rejeu d’une action restaurée en `running`

Un `ActionRecord` synthétique en état `running` a été restauré par `ActionExecutor.from_snapshot()`. Un handler compté a ensuite été appelé par `execute()`.

Résultat observé :

```text
P0-A succeeded handler_calls= 1 restored_status= succeeded
```

Constat : la restauration ne convertit ni ne bloque l’état `running`; le chemin normal d’exécution considère cet enregistrement comme rejouable. Dans le cas réel d’un effet externe, ce comportement peut produire un double effet après interruption.

### P0-B — identité d’idempotence incomplète

Une requête terminée a été enregistrée avec une clé donnée. Une requête portant la même clé mais un budget ou des préconditions différents n’a pas été rejetée comme collision. Elle a été traitée comme un replay du premier résultat :

```text
P0-B budget accepted_as rejected replay= True
P0-B precondition accepted_as rejected replay= True
```

Constat : `ActionExecutor.request()` compare seulement mission, plan, étape, outil et `parameters`. Les permissions effectives, préconditions, budget/limites et version de contrat ne participent pas à l’identité. Le résultat rejoué peut en outre être `rejected` pour une raison issue de la première exécution, ce qui masque la demande différente.

### P0-C — exception inattendue après démarrage

Un handler enregistré a levé `KeyError`, exception non couverte par le tuple actuel. L’exception est remontée, mais l’enregistrement est resté non terminal :

```text
P0-C exception= KeyError status_after= running
```

Constat : le handler est appelé après la transition et le journal `action_started`, mais une exception inattendue laisse l’état `running`. Une reprise ultérieure pourrait alors rejouer un effet dont l’existence est inconnue.

## Constats complémentaires

* La restauration du runtime abandonne correctement les missions `in_progress`, mais ne réconcilie pas les `ActionRecord` individuels en `running`.
* Le journal est chaîné et vérifiable, mais une erreur de persistance déclenchée par `_changed()` peut survenir après mutation mémoire; le chemin d’exception doit donc distinguer échec avant démarrage, après démarrage et effet possiblement produit.
* Le verrou `RLock` protège les exécuteurs partageant un même processus uniquement. `PostgresSnapshotStore.save()` utilise un upsert sans version attendue, verrou explicite ou CAS inter-processus. La garantie multi-writer n’est donc pas prouvée et doit rester explicitement hors périmètre : modèle single-writer.
* Les outils déterministes appliquent déjà une allowlist et une racine workspace contrôlée. Il n’existe pas de sandbox de processus ni de timeout matériel pour interrompre un handler Python arbitraire; Phase 4.1 doit limiter et documenter ce qui est effectivement contrôlable, sans prétendre à une isolation inexistante.
* La suite héritée était verte avant ce mandat (`110 passed, 2 skipped` selon le contexte de reprise). Les nombres finaux devront être régénérés après ajout des preuves Phase 4.1, et les rapports/matrices devront utiliser la même source de vérité.

## Corrections exigées par priorité

1. Introduire une sémantique persistante d’action interrompue/inconnue et interdire tout rejeu automatique d’une action restaurée `running`.
2. Calculer une empreinte canonique complète couvrant mission, plan, étape, outil, paramètres normalisés, préconditions, permissions pertinentes, budgets/limites et version de contrat; refuser toute collision de clé.
3. Rendre terminal/cohérent tout chemin d’exception, en particulier après `action_started`, avec état `uncertain` dès qu’un effet peut avoir été produit.
4. Ajouter les tests unitaires, intégration, crash réel, restauration, concurrence in-process, budgets, permissions et CORE_ONLY, puis six démonstrations JSON/Markdown reproductibles.
5. Documenter la restriction single-writer PostgreSQL tant qu’aucun CAS multi-processus réel n’est démontré.

Ce rapport est volontairement antérieur aux corrections et ne revendique aucune garantie Phase 4.1 supplémentaire.
