# Contrats techniques du moteur cognitif CIEL

Ces contrats sont une spécification de préparation. Ils ne déclarent pas les
composants comme implémentés.

## Règles communes

- Tous les identifiants de mission, plan, étape, action et observation sont des UUID stables.
- Toute mutation importante est un événement append-only dans le Mission Ledger.
- Les payloads sont versionnés et validés par schéma.
- Les erreurs sont distinguées : refus de policy, précondition invalide, erreur d’outil, observation inconnue, postcondition échouée, budget épuisé.
- `PASS` nécessite une preuve indépendante ; `PARTIAL` signifie résultat insuffisamment prouvé.

## Goal / Mission

```text
Mission {
  mission_id, schema_version, objective, context,
  constraints {deadline, budget_usd, max_steps, max_retries, max_wall_time_s},
  execution_mode: CORE_ONLY | AI_ASSISTED,
  approval_policy, created_at
}
```

Invariant : aucune mission ne peut octroyer elle-même une permission d’outil.

## Plan / Step

```text
Plan { plan_id, mission_id, version, steps[], created_by, rationale, digest }
Step {
  step_id, plan_id, ordinal, depends_on[], action_ref,
  preconditions[], postconditions[], idempotency_key,
  status, retry_policy, resource_limit
}
```

Transitions autorisées : `planned -> ready -> running -> observed -> verified`,
avec sorties `failed`, `blocked`, `abandoned` et `human_review`.

## Strategy Engine

Entrée : mission, observations, mémoire consultative et policy.  
Sortie : `StrategyProposal` versionnée avec justification, étapes affectées,
risques et coût estimé.  
Interdit : exécuter un outil, modifier la policy ou déclarer `PASS`.

## Tool Registry / Action Executor

```text
ToolSpec {
  name, version, input_schema, output_schema, permissions,
  sandbox_profile, reversible, dry_run_supported, timeout_s, cost_profile
}
ActionRequest {
  action_id, step_id, tool_name, tool_version, arguments_digest,
  idempotency_key, approval_id, budget_reservation
}
ActionResult {
  action_id, status, effect_state: none|applied|reversed|unknown,
  output_digest, error_class, started_at, finished_at, actual_cost
}
```

Un `effect_state=unknown` interdit le replay automatique.

## Observation / Verification

```text
Observation {
  observation_id, action_id, source, payload_digest,
  effect_state, captured_at, provenance
}
VerificationResult {
  target_id, verdict: PASS|FAIL|PARTIAL,
  criteria[], evidence_refs[], verifier_version
}
```

Le verifier consomme des observations et postconditions, pas seulement le
texte d’un fournisseur.

## Memory Core

`MemoryRecord` garde une provenance vers mission, report digest et plage du
journal. Les statuts sont `hypothesis`, `corroborated`, `invalidated`.
Une SkillCard est `candidate` après une source et `corroborated` seulement
après deux missions distinctes et non contradictoires. Retrieval retourne
provenance, fraîcheur, portée et contradictions ; il ne donne aucune autorité.

## Mission Ledger

Événements minimaux : `mission_accepted`, `plan_created`, `step_ready`,
`policy_decision`, `action_requested`, `action_completed`, `observation_added`,
`verification_completed`, `strategy_revised`, `human_approval_requested`,
`mission_interrupted`, `mission_completed`.

Chaque événement contient `event_id`, `mission_id`, `plan_id`, `step_id` si
applicable, `causation_id`, `correlation_id`, `schema_version`, timestamp,
acteur, payload digest et chaîne précédente.

## Recovery Manager

```text
RecoveryDecision {
  action: continue|retry|revise|human_review|abandon,
  reason, evidence_refs, safe_to_replay, remaining_budget
}
```

`retry` est permis uniquement si l’outil et la policy l’autorisent et si la
clé d’idempotence est conservée. `continue` exige une postcondition vérifiée.

## Budget Manager

Réservation avant action, réconciliation après action, refus si budget,
deadline, tokens, étapes ou temps sont épuisés. Les coûts estimés et réels
sont conservés séparément dans le ledger.

## Policy / Safety

Entrée : mission, action, outil, contexte et état.  
Sortie : `allow`, `deny` ou `requires_human_approval`, avec policy version et
raison. La policy est immuable pendant une action.

## Self-Diagnostics

Doit exposer : `journal_valid`, `store_available`, `policy_version`,
`providers_configured`, `memory_enabled`, `active_missions`, `unknown_effects`
et les limites courantes. Le diagnostic ne modifie aucun état métier.
