# Nexus Ciel

Nexus Ciel is an evolving, self-hosted mission runtime. The repository is not yet a production-ready autonomous cognitive operating system. Its current work is focused on truthful mission outcomes, durable state, provider integration, bounded spending, and verifiable execution.

## Current branch

Finalization work is isolated on `work/ciel-finalization-2026-11-05` and proposed in [PR #10](https://github.com/nkinzogomer-eng/nexus-ciel/pull/10). Nothing in this branch has been merged into `main`.

The persistence candidate has passed PostgreSQL process-kill/restart recovery tests and a Docker Compose full-stack stop/start with a named PostgreSQL volume. It verified restoration of mission state, report, and Mission Journal integrity.

Further work has since added deterministic verification, budget enforcement, and an OpenAI-compatible provider adapter. These newest changes must pass their own CI run before being treated as validated.

## Important execution semantics

A provider response is not proof that the mission objective was achieved.

- `PASS`: a supplied, supported deterministic verification contract passed.
- `FAIL`: execution or a supported verification contract failed.
- `PARTIAL`: output exists but no adequate deterministic acceptance oracle was supplied, or the supplied oracle is unsupported.

The verifier currently supports `contains_all`, `contains_any`, `exact_match`, `json_valid`, and `non_empty`. These are output-contract checks, not general semantic proofs. Complex missions still need task-specific executable oracles and independent validation.

The model's configured routing-confidence value is used only to select a provider stage. It is not treated as evidence of correctness.

## Provider configuration

Production API startup no longer silently enables the synthetic providers used by tests. Copy `.env.example` to `.env`, configure an actual OpenAI-compatible endpoint, then start the Compose stack. The API container receives the configured values explicitly; the example uses `host.docker.internal` for a model server running on the host. The variables are:

- `NEXUS_LLM_BASE_URL`
- `NEXUS_LLM_MODEL`
- optional `NEXUS_LLM_API_KEY`
- `NEXUS_LLM_STAGE`
- timeout, maximum output tokens, routing hint, and token prices

For hosted endpoints, explicit input and output token prices are required so the mission budget guard can estimate costs. The current adapter supports one configured endpoint; retry policies, circuit breakers, multiple live provider profiles, and tool/function calling remain unfinished.

Synthetic `LocalProvider` and `SecondaryProvider` implementations are enabled only by the test environment. Do not set `NEXUS_TEST_MODE=1` in production.

## Mission budget

A mission's `constraints.budget_usd` is checked before provider calls. Estimated and actual costs are checked across the cumulative escalation path. If a provider's actual charge exceeds the declared budget, the mission fails and the overspend is recorded; a charge already made by a provider cannot be undone.

## Crash policy

A persisted mission found in `in_progress` after restart is not automatically replayed. It is marked `abandoned`, any stale `PASS` report is replaced by an honest interruption `FAIL`, and `mission_interrupted` is appended to the journal. Automatic resume remains disabled until deterministic replay and idempotency are proven.

## Still required before calling CIEL finalized

- hosted production connectors with stronger isolation, approval, and reversible actions;
- persistent telemetry, cache expiry, Memory Core, and evidence-backed SkillCards;
- retries, timeouts, circuit breakers, and tested provider failover;
- human approval and intervention paths;
- long-running mission orchestration and restart-safe checkpoints;
- operational interface and deployment validation, including Telegram if retained as the remote interface;
- independent end-to-end missions that prove useful outcomes, not merely that a model returned text.

See [REPRISE.md](REPRISE.md) for the detailed state, evidence, and next gates.

## Deterministic plans and bounded tools

Missions may include `constraints.plan`, an ordered list of `generate` and `tool` steps. The compiler rejects duplicate IDs, unsupported step kinds, forward dependencies, and invalid fallbacks. The planner executes only the declared plan; it does not let a model grant itself capabilities. A mission without a plan compiles to one generation step for compatibility.

Tool steps must name a registered tool and the mission must list that tool in `constraints.allowed_tools` and grant every required permission in `constraints.permissions`. The built-in registry accepts only idempotent, read-only handlers. Each tool call runs with a timeout. A declared `fallback_to` can redirect a failed tool step to a later step; completed steps are not replayed, and the replan is recorded in the Mission Journal. Write-capable tools, human approval, and external sandboxing are not implemented.

Execution limits default to 60 seconds, 8 steps, 8,192 cumulative provider tokens, and 5 seconds per tool call. Missions can tune these positive limits in `constraints.deadline_seconds`, `max_iterations`, `max_tokens`, and `tool_timeout_seconds`, within system maxima of 300 seconds, 32 steps, 32,768 tokens, and 30 seconds per tool call. The cumulative token limit is checked after each provider response, before the next step; a response that itself exceeds the cap has already been paid for. The spending guard remains responsible for budget enforcement. An interrupted persistent mission is still abandoned on process restart; plans and step checkpoints are not used for automatic replay.

Run `python -m nexus.autonomy_demo` for the offline controlled demonstration. It uses fixture tools and the synthetic local provider; it is evidence of orchestration and verification behavior, not a production connector test.
