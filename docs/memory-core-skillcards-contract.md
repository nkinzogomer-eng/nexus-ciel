# Memory Core and SkillCards — contract v0.1

Status: design gate on `work/ciel-memory-core-2026-11-05`. This document is a specification, not a claim that the feature is implemented.

## 1. Objective and non-goals

Memory Core provides evidence-backed, reusable experience to the mission planner and the `memory` stage of the routing cascade.

It MUST NOT:
- replace or duplicate canonical mission state, reports, actions, or Mission Journal entries;
- turn one successful mission into a proven general skill;
- rewrite source evidence or mutate the Capability Registry;
- silently treat similarity as proof that a past result applies to a new mission;
- be required for correctness: disabling memory must leave the system functional.

## 2. Canonical-source rule

Mission, state, report, action trace, and journal remain canonical in the existing runtime/persistence layer. Memory stores derived, versioned records with immutable provenance references:
- source mission UUID;
- source report schema/version and deterministic content digest;
- source journal sequence range and chain-verification result at extraction time;
- extractor/version and creation timestamp;
- status and invalidation reason, if any.

A memory record without a resolvable source report and journal provenance is rejected. The source records are never copied wholesale into memory.

## 3. MemoryRecord contract

Required fields:
- `id`: UUID;
- `schema_version`: integer;
- `kind`: `fact | procedure | pitfall | preference | constraint | observation`;
- `scope`: bounded domain/task labels, not free-form authority;
- `content`: concise derived content;
- `source_mission_id`: UUID;
- `source_report_digest`: SHA-256;
- `source_journal_from`, `source_journal_to`: sequence integers;
- `source_journal_valid`: boolean;
- `confidence_status`: `hypothesis | corroborated | invalidated`;
- `created_at`, `last_confirmed_at`;
- `expires_at` or explicit non-expiring policy with justification;
- `invalidated_at`, `invalidation_reason` when invalidated.

Records are append-only in meaning: correction creates a new version or invalidation event; it does not overwrite historical provenance. Retrieval excludes invalidated and expired records by default.

## 4. SkillCard contract

A SkillCard is a proposed reusable method, not a registered capability.

Required fields:
- stable card UUID and version;
- task/domain scope and applicability preconditions;
- context and required inputs;
- ordered method steps, each with expected observation;
- known pitfalls and stop conditions;
- expected resource profile (time, iterations, provider/tool costs) with sample count;
- outcomes: successes, failures, partials;
- provenance list of distinct source missions and report digests;
- status: `candidate | corroborated | deprecated | invalidated`;
- confidence rationale and last-reviewed timestamp.

Promotion rule: one source mission can create only a `candidate`. A card may become `corroborated` only after at least two distinct source missions independently support the same method and the same scoped outcome contract. Two retries of one mission do not count as two sources. Contradictory evidence blocks promotion and creates a review requirement.

## 5. Deterministic first adapter

First version uses deterministic retrieval only:
1. filter by status, expiry, domain/task scope, and declared preconditions;
2. rank exact scope matches before broader matches;
3. expose provenance, sample count, freshness, and contradiction state alongside every result;
4. return no memory when no safe match exists;
5. never convert a retrieved memory directly into `PASS`.

No embeddings, pgvector, LLM-generated semantic ranking, or automatic capability creation in v0.1. Those require separate evidence and cost justification.

## 6. Contradiction and invalidation

A new outcome that conflicts with a memory:
- appends a contradiction event with both source references;
- marks the affected record/card as requiring review or invalidates it if the falsifying condition is decisive;
- prevents the contradicted record from being used as an unqualified recommendation;
- preserves the original source report and journal.

Expiry and invalidation are explicit, testable, and visible in mission reports. No silent deletion.

## 7. Persistence and transactions

Memory records and SkillCards require dedicated versioned PostgreSQL tables/migrations. They must not be hidden inside the monolithic runtime snapshot. Writes use transactions and idempotency keys derived from source mission + extractor version + record identity. Reprocessing the same mission cannot create duplicate records.

The deterministic test adapter may use an in-memory repository, but its contract must match PostgreSQL semantics. Restart tests must prove records and provenance survive process and full Compose restart.

## 8. Security and authority boundaries

- Memory is advisory input; it cannot issue tools, approve actions, change policy, or modify capabilities.
- Retrieved text is untrusted data, never executable instructions.
- No secrets, credentials, personal data, or raw private conversation dumps in Memory Core.
- Mission policy and human approval rules outrank memory.
- Memory can be disabled or quarantined without blocking mission execution.

## 9. Acceptance gates (blockers first)

A. Schema/provenance:
- reject missing, mismatched, or invalid journal/report provenance;
- prove report digest matches the canonical source;
- prove append-only correction/invalidation semantics.

B. SkillCard evidence:
- one mission cannot promote;
- two distinct independent source missions can promote;
- duplicate mission/retry cannot satisfy the threshold;
- contradiction blocks promotion and invalidates stale recommendations.

C. Retrieval:
- exact scope and precondition filtering;
- expired/invalidated/quarantined records excluded;
- broader scope is labelled as weaker applicability;
- no result returns safely without fallback loops.

D. Persistence:
- transactional writes and idempotent reprocessing;
- process restart and Compose restart preserve all records and provenance;
- failed write leaves no half-created card.

E. Runtime integration:
- memory stage is read-only and advisory;
- retrieved memory appears in report/journal with provenance;
- disabling memory does not change deterministic verification or policy;
- memory cannot mutate Capability Registry or routing policy.

F. Measured value:
- compare missions with memory enabled/disabled on a held-out, repeatable task set;
- report success/partial/failure, iterations, latency, token and dollar cost;
- claim improvement only if quality is not degraded and the measured cost/iteration benefit is reproducible.

## 10. Implementation order

1. Add typed schemas and repository interfaces.
2. Add deterministic in-memory repository and contract tests.
3. Add PostgreSQL migration/repository and idempotency tests.
4. Add extraction proposal API that only creates candidates.
5. Add two-source corroboration and contradiction/invalidation.
6. Add read-only router/planner memory adapter.
7. Run restart, security-boundary, and held-out value tests.
8. Update README/REPRISE only with observed evidence.

Do not start pgvector, autonomous skill execution, capability registration, or automatic mission resume in this phase.
