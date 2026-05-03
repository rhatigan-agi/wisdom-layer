# Changelog

All notable changes to the Wisdom Layer SDK are recorded in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.0] -- 2026-05-03

Multi-agent release — adds the `wisdom_layer.workspace` surface so
multiple agents can share a backend, contribute to a shared memory
pool, walk cross-agent provenance back to the contributing private
memory, message each other directly, and run a Team Dream phase that
synthesizes team insights from cross-agent contributions. Multi-agent
features are Enterprise-tier; Free / Pro / Team / Business retain the
v1.1.0 single-agent feature set. This release also rolls in the
commercial restructure (Business tier, monthly + annual billing, EULA
rewrite) and the demo-pool slot reservation that ships alongside it.

### Added — Multi-agent workspace (Enterprise)

- **`Workspace` and `WorkspaceSQLiteBackend` / `PostgresWorkspaceBackend`.**
  The shared backend that holds all cross-agent state for a
  multi-agent deployment: agent directory, shared memory pool, team
  insights, cross-agent provenance events, and the agent message bus.
  Construction validates an Enterprise license against the
  `multi_agent_workspace` feature gate; Free / Pro keys raise
  `TierRestrictionError` at `Workspace.initialize()`. Per-agent state
  (memories, facts, directives, journals) continues to live in each
  agent's own `BaseBackend` — the workspace never copies private
  content. Configurable `max_agents` cap with structured
  `TierRestrictionError(cap_kind="agents", current=, limit=)` on
  overflow.
- **`AgentDirectory` (read-only) and `Workspace.register_agent()`.**
  Capability-tagged roster of registered agents with `registered_at`,
  `last_seen_at`, `past_success_rate` (schema ships at 0.0 for v1.2.0;
  the closed-loop writer lands in v1.3.0), and soft-archive support.
  `directory.list(capability=, active_within=, include_archived=)`
  filters; `directory.get(agent_id)` returns the row including
  archived entries so callers can distinguish "never registered" from
  "since unregistered." Re-registering an active agent updates
  capabilities without consuming a new `max_agents` slot.
- **`SharedMemoryPool` (the moat).** Workspace-scoped pool that holds
  back-references to contributing agents' private memories. Public
  surface: `pool.promote(...)`, `pool.endorse(...)`,
  `pool.contest(...)`, `pool.list_shared(...)`, `pool.search(...)`,
  `pool.synthesize_team_insight(...)`,
  `pool.walk_provenance(team_insight_id)`. A contributing agent's
  private memory is back-referenced via
  `shared_memory_pool.source_memory_id` — never copied. Compromising
  `workspace.db` never exposes private memory content. Endorsements
  and contentions are atomic and idempotent (composite PK + INSERT OR
  IGNORE); `team_score` is denormalized for ranked retrieval.
- **`agent.memory.share(memory_id, *, visibility=, reason=)`.** Bridge
  from a per-agent memory into the workspace pool. Tenancy-checked: the
  bridge calls `get_memories_by_ids(agent_id=self._agent.agent_id, ...)`
  so an attempt to share another agent's memory id raises
  `ValueError`. Idempotent — re-sharing returns the same deterministic
  `shared_memory_id` (sha256 of contributor + source memory id, 16
  hex chars). Emits a cross-agent `MEMORY_SHARED` provenance event.
- **`agent.provenance.walk_xagent(team_insight_id)`.** Returns a
  `TeamInsightProvenance` with the team insight, its contributing
  `SharedMemory` rows, and each contribution's `source_memory_id`
  back-pointer into the contributor's per-agent backend. The walk
  does not — and cannot — dereference any `source_memory_id`; only
  the contributing agent itself can resolve those ids via
  `agent.memory.get(memory_id)`. The patent-defensible isolation
  invariant is encoded in the type system: `TeamInsightProvenance`
  and `ProvenanceContribution` carry no field for cross-agent private
  content, and the public surface is pinned by a contract test that
  introspects `dataclasses.fields()` so any future addition that would
  broaden the boundary requires deliberately editing the test.
- **Team Dream Phase 1 — `dreams.run_team_dream()`.** Cross-agent
  reconsolidation pass that synthesizes team insights from shared
  memories scored above a threshold. Phase 1 ships the synthesizer
  and the scoring pipeline; Phases 2–5 (cross-agent endorsement
  weighting, decay, contention resolution, anti-loop) land in v1.3.0.
- **`MessageBus` and `agent.messages.*` (Multi-C).** Eight-method
  agent-to-agent messaging surface routed through the workspace bus:
  `send`, `broadcast`, `reply`, `check_inbox`, `list_thread`,
  `list_agents`, `mark_read`, `close_thread`. The bridge auto-fills
  `sender_id` from `self._agent.agent_id` (impersonation guard) and
  reads `recipient_capabilities` from the workspace directory rather
  than from the caller (stale-local-view guard). Rate limits: 100
  messages per agent per hour; 10 broadcasts per agent per hour
  (counts against the 100/hr total). Past-deadline pending messages
  lazy-expire on the recipient's next inbox read. Threading is
  reply-driven: replies inherit the parent's `thread_id`; threads
  close idempotently and refuse subsequent replies. Full provenance:
  every send / reply / broadcast / close emits a cross-agent
  provenance event (`MESSAGE_SENT`, `MESSAGE_REPLIED`,
  `MESSAGE_BROADCAST`, `THREAD_CLOSED`).
- **`WORKSPACE_TOOLS` and `execute_tool(...)`.** Five Anthropic-format
  JSON tool schemas (`send_message_to_agent`, `list_agents`,
  `check_inbox`, `reply_to_message`, `broadcast`) plus a dispatcher
  that maps a tool-use response onto the matching `agent.messages.*`
  method. Schemas port cleanly to OpenAI `functions` (rename
  `input_schema` → `parameters`) and to LiteLLM. Unknown tool names
  return `{"error": "unknown_tool", "name": ...}` rather than raising,
  so the LLM sees the error and self-corrects on the next turn.
  `reply_deadline_hours` (LLM-friendly relative time) is coerced to
  an absolute UTC `datetime` anchored at the agent's clock.
- **`ThreadExitPolicy` triple-gate (Multi-C Chunk D).** Frozen
  dataclass — `max_turns` (deterministic ceiling, default 10),
  `stagnation_check` (cosine similarity over the last two message
  bodies, deterministic given embeddings), `convergence_check` (LLM
  judge classifies the thread as `CONVERGED` or `OPEN`,
  opportunistic). Gates fire in priority order — `max_turns` always
  evaluated first because it costs nothing and provides the
  guaranteed-termination property. Stagnation and convergence are
  silent-skipped when the caller does not supply an embedder / judge,
  letting application code run a deterministic-only configuration in
  CI / tests without changing the policy object. Tuning constants
  (`STAGNATION_COSINE_THRESHOLD`) and the convergence judge prompt
  live in the compiled `_internal/thread_exit.py`.
  `MessageBus.evaluate_thread_exit()` is the recommended entry point —
  it auto-closes when a gate fires, persists `similarity` and
  `judge_verdict` into the closure metadata, and is idempotent on
  already-closed threads.
- **`wisdom-layer-migrate` CLI.** New `[project.scripts]` entry —
  `wisdom-layer-migrate up` runs the per-agent and workspace migration
  sets against a target backend. Includes `--dry-run`, pre-flight
  drift detection, and JSON status output. Required for upgrading
  existing v1.1.0 stores in place: migration `0024_facts_source_ids`
  ships in this release (see Changed below).
- **New exception classes.**
  - `MessageRateLimitExceededError` — raised by `agent.messages.send /
    broadcast / reply` when the per-agent or broadcast cap trips.
    Carries `cap_kind`, `current`, `limit`, and `reset_at` fields.
  - Existing `TierRestrictionError` extended with `cap_kind="agents"`
    for the workspace `max_agents` cap.

### Changed

- **Schema-half of per-fact provenance graph: `facts.source_memory_ids`
  column.** Migration `0024_facts_source_ids` adds a new
  `source_memory_ids` column to the `facts` table (JSON array on
  SQLite, `text[]` on Postgres) and idempotently backfills existing
  rows from the legacy scalar `source_memory_id`. **No application
  surface change in v1.2.0** — the SDK continues to read and write the
  legacy scalar; the column lives on disk so downstream products and
  the in-flight v1.2.1 work can populate it without a second migration
  step. The public API (`Fact.source_memory_ids` as the primary field
  and `agent.facts.trace()`) lands in v1.2.1. Run `wisdom-layer-migrate
  up` on existing stores to apply the migration ahead of the v1.2.1
  upgrade, or let the agent's normal `initialize()` apply it on first
  v1.2.0 boot. See the
  [migration guide](docs/migrations/v1.2.0-fact-source-ids.md).

### Commercial restructure (pricing, tiers, EULA)

- **New tier shape: Free / Pro / Team / Business / Enterprise.**
  Business is a new fifty-seat tier sitting between Team and Enterprise
  for engineering organizations standardizing on Wisdom Layer across
  multiple internal teams. Pro / Team / Business share an identical SDK
  feature set; they differ only in licensed seat count (1 / 10 / 50)
  and shared billing scope.
- **Pricing locked.** Pro $189/mo or $1,890/yr (~17% off) · Team
  $749/mo or $6,990/yr (~22% off) · Business $2,490/mo or $22,500/yr
  (~25% off) · Enterprise from $36,000/yr annual contract. Team seat
  count was raised from 5 to 10 in this release. See
  [wisdomlayer.ai/pricing](https://wisdomlayer.ai/pricing) — the live
  page is the canonical reference.
- **Monthly + annual billing on Pro / Team / Business.** The signup
  flow exposes both periods with a Monthly / Annual toggle; annual
  surfaces the per-tier savings inline. Stripe price-id → plan-name
  mapping is maintained server-side via the `plan_label_for_price`
  helper so dashboards, receipts, and the welcome email all render the
  same plan label.
- **Enterprise tier reframed around use-rights.** The Enterprise card
  and EULA both lead with the use-rights gate — required whenever an
  agent serves an end user other than the licensee, including
  customer-facing products, multi-tenant deployments, embedded /
  white-label / OEM distribution, and regulated environments. SDK
  feature deltas (multi-agent mesh, custom dream phases, cross-agent
  memory and dream cycles) are still on the v1.3.0 roadmap.
- **`EULA.md` rewritten** to match the five-tier shape: Business tier
  added in §4, Team raised to 10 seats, Enterprise rewritten to lead
  with use-rights, monthly + annual billing language, and a downgrade
  preservation clause confirming that on voluntary downgrade or
  cancellation accumulated memories, facts, and directives are
  preserved on disk while paid-tier features stop running.
- **`LICENSE` rewritten** to match: §1 "Tier" definition enumerates
  Free / Pro / Team / Business / Enterprise and adds use-rights
  language; §3 "Tier Limits" enumerates seat counts (1 / 10 / 50) and
  the Enterprise use-rights gate (customer-facing, multi-tenant,
  embedded, white-label, OEM, regulated); §11 "Entire Agreement"
  updated to reference the Pro / Team / Business / Enterprise
  subscription agreements.
- **`docs/tiers.md` rewritten** to match: at-a-glance matrix expanded
  from three columns to five, with Pro / Team / Business identical for
  every SDK feature row and a new use-rights row gating
  customer-facing / multi-tenant / OEM / white-label deployments to
  Enterprise. Pricing rows split into monthly and annual. Pro / Team /
  Business sections added with seat counts, shared billing scope, and
  the use-rights restriction; Enterprise section reframed around
  use-rights.

### Added

- **Welcome email cadence on `/v1/license/free`.** New customers
  receive a first-signup welcome email; returning customers receive a
  contextual welcome-back email — one of three variants (free returner
  with active trial showing days remaining, free returner with expired
  trial including a `/pricing` upgrade nudge, or paid returner). Send
  is fail-soft via Resend; cooldown is 24 hours per license, tracked
  via the new `licenses.last_welcome_email_sent_at` column. Cooldown
  stamps unconditionally on dispatch attempt (not on success) to
  prevent retry storms when Resend rejects. Migration:
  `005_welcome_email_cadence.sql`. Helper module:
  `api/src/wisdom_api/email.py`.
- **Tier-priority license lookup on `/v1/license/free`.** The
  existence-check query now selects the highest-tier license for a
  given email (`ORDER BY CASE tier WHEN 'enterprise' THEN 0 WHEN 'pro'
  THEN 1 ELSE 2 END`). Closes a duplicate-license bug where a paid
  customer hitting the free funnel previously slipped through the
  `WHERE tier = 'free'` filter and silently received a second Free
  license.
- **`plan_label_for_price` helper.** Centralized Stripe price-id →
  plan-name mapping (e.g., `price_1ABC...` → `"Pro (annual)"`) used
  by the signup flow, dashboard, receipt rendering, and welcome
  emails so the displayed plan label is consistent across surfaces.
- **Demo-pool slot reservation and reconciliation.** The hosted demo
  funnel at [wisdomlayer.ai/try](https://wisdomlayer.ai/try) now
  reserves a slot atomically before spawning a session and
  reconciles slot state against the running pool, so capacity is
  enforced even under concurrent submissions. Visitors arriving when
  the pool is full are routed to a new at-capacity page that explains
  the wait and offers a notify-me path.
- **At-capacity page** at `/try/coming-soon` for the demo pool. Honest
  copy for both the pre-launch state and the failure-redirect path
  used by the gated try-stub Netlify function (honeypot / Turnstile /
  rate-limit / transient errors all silently land here so bots get no
  iteration signal).
- **Pricing page rebuild.** `/pricing` rewritten with a five-tier card
  layout, Monthly / Annual toggle, expanded comparison table, and a
  v1.2.0 / v1.3.0 roadmap section in the FAQ.

### Changed

- **Team tier seat count raised from 5 to 10** under the same
  per-organization shared-billing structure. Existing Team licenses
  retain their seat allowance under the new umbrella; renewals move
  to the published Team price.

---

## [1.1.0] -- 2026-04-29

Commercial restructure release. The cognitive substrate is unchanged;
this release introduces the tier and trial mechanics needed to ship
Wisdom Layer as a commercial product, plus an anonymous opt-out
telemetry channel on the Free tier so we can answer real questions
about adoption without compromising customer privacy.

**Headline changes:**

- **14-day full Pro trial on signup** — every new Free signup includes
  a 14-day trial with all Free capacity caps lifted and the full Pro
  cognitive substrate unlocked. No credit card.
- **Free-tier capacity caps** — 3 agents, 1,000 memories per agent,
  1,500 messages per rolling 30-day window. Hard-enforced in-process
  by the SDK with structured `TierRestrictionError` carrying
  `cap_kind`, `current`, `limit`, `reset_at`, and `upgrade_url` fields.
- **Anonymous opt-out telemetry on Free** (counts only, no content,
  no PII). Pro and Enterprise are silent by default. Disable at any
  time with `WL_TELEMETRY=0`. Full disclosure in
  [docs/telemetry.md](docs/telemetry.md).
- **Pricing locked.** Pro $99/mo · Team $249/mo · Enterprise starts at
  $24K/yr (contact sales). See
  [wisdomlayer.ai/pricing](https://wisdomlayer.ai/pricing).

### Added

- **`docs/telemetry.md`** — full disclosure of the anonymous usage
  telemetry channel: payload schema, cadence (~600 bytes/day per
  install), endpoint, retention (12 months for raw, indefinite for
  aggregates), opt-out wipe path, security-review notes, and audit
  pointer to the in-wheel `wisdom_layer/_telemetry.py` source.
- **`TierRestrictionError` cap-violation mode.** The existing exception
  now carries optional `cap_kind` / `current` / `limit` / `reset_at` /
  `upgrade_url` fields when raised from a capacity cap (vs feature-gate
  mode where `cap_kind is None`). Maps cleanly to HTTP 402 vs 403 in
  framework adapters.
- **Stateless Pro trial mechanic.** Trials are encoded directly in the
  signed JWT (`trial_ends_at` and `tier_at_expiry` claims). The SDK
  compares against its clock on every entitlement check; no server
  round-trip at expiry. Trials downgrade in-process to
  `tier_at_expiry` (default `free`). Existing data is preserved.
- **Account dashboard page** (in `wisdom-layer[dashboard]`). Shows
  trial countdown, live cap progress bars (memories / messages /
  agents), telemetry status, and upgrade CTAs. Health page shows
  inline cap-warning banners as you approach a threshold.
- **Configuration env vars** documented in `docs/config.md`:
  `WL_TELEMETRY` (opt-out / opt-in), `WL_TELEMETRY_ENDPOINT`
  (override for proxy / air-gap deployments).
- **`ResourceLimits` Free-tier cap fields** — `max_agents_free=3`,
  `max_memories_free=1_000`, `max_messages_per_30d_free=1_500`.
  Tier-bound, orthogonal to deployment presets — `for_local()` /
  `for_cloud()` / `for_small_model()` explicitly do not override them,
  and a parametrized regression test pins this invariant.
- **Quickstart "Free-Tier Capacity Caps" section** with the recommended
  `try / except TierRestrictionError` recipe for cap branching.
- **`memory.capture(..., created_at=)`** — explicit override for the
  captured timestamp, gated by validation: must be timezone-aware, in
  the past per the agent's clock, and within the last 10 years
  (`ValueError` otherwise). Naive datetimes, future timestamps, and
  suspected epoch / timezone errors all raise. Intended for migration
  imports that need to preserve original `created_at` values; live
  capture should continue to omit the argument so the agent's clock
  stamps the row. Reinforcement and decay still run against wall-clock
  elapsed time on the row's `updated_at` / `accessed_at` columns —
  `created_at` only governs ordering and lookback windows.
- **`memory.export(..., kinds=)`** — restrict an export bundle to the
  listed `event_type` values (e.g., `kinds=["session_record"]` for a
  session-history-only backup). Same semantics as `memory.search(kinds=)`
  added in v1.0. Omitting the argument exports every event type
  (existing behavior preserved).
- **`event_types=` alias** for `kinds=` on both `memory.search` and
  `memory.export`, for callers who reach for the more literal name.
  Passing both raises `ValueError` so the contract stays unambiguous.
- **`dreams.trigger(phases=, lookback_days=)`** — execute a subset of
  the five dream-cycle steps (`reconsolidate`, `evolve_directives`,
  `critic_audit`, `directive_decay`, `journal_synthesis`) and / or
  bound the reconsolidate step's candidate window. Caller-supplied
  `phases` ordering is normalized to canonical execution order so cycle
  semantics stay deterministic. `lookback_days` mirrors the parameter
  on `dreams.estimate_cost` and `memory.consolidate` — useful when
  historical imports preserved `created_at` and you want recent
  activity only. Defaults are unchanged: `trigger()` with no args still
  runs all five steps with no time filter.

### Changed

- **`AgentConfig.retry_policy` default flipped from `None` to a real
  `RetryPolicy()`** (3 attempts, exponential backoff with jitter).
  Pre-1.1 the default was `None`, which silently meant "no retries"
  — a production footgun. **Behavior change for callers that did not
  set the field explicitly:** transient `LLMRateLimitError`,
  `LLMTimeoutError`, and `LLMServerError` errors now retry up to 3
  times before surfacing. Callers that explicitly want the old
  zero-retry behavior should pass `retry_policy=RetryPolicy(max_attempts=1)`;
  passing `retry_policy=None` is still accepted and continues to mean
  "no retry wrapper installed". Side-effect calls (critic audit,
  coherence checks) remain intentionally non-retryable.
- **README and SECURITY** — privacy framing softened from "no
  telemetry" to "no content, prompts, memories, or agent data ever
  leaves your infrastructure; Free sends a small anonymous daily
  count-payload, full disclosure linked." Pro/Enterprise privacy
  guarantee unchanged: silent by default.
- **EULA** — section 4 (tier limits) now distinguishes Pro use rights
  (internal tools / production systems your team operates) from
  Enterprise (customer-facing, multi-tenant, embedded, white-label,
  OEM). Section 5 (data handling) adds the explicit telemetry
  consent clause.
- **`docs/tiers.md`** — fully rewritten to match the new caps,
  trial, and telemetry policy. Capability matrix now lists agent /
  memory / message caps per tier with hard-cap vs advisory-cap
  annotation. Adds a dedicated Trial section.
- **`docs/integration-guide.md`** — adds "Cap Violation Handling"
  section showing the `cap_kind` branch and HTTP-402 vs HTTP-403
  mapping.

### Compatibility

- **Existing license keys continue to work.** Tokens issued without
  `trial_ends_at` / `tier_at_expiry` claims behave identically to v1.0.x
  (no trial, tier as encoded). The new claims are additive.
- **`TierRestrictionError` callers are unaffected.** Existing handlers
  that read `e.feature` / `e.required_tier` continue to work
  unchanged; new handlers can branch on `e.cap_kind is not None`.
- **Telemetry can be disabled before any data is sent** by exporting
  `WL_TELEMETRY=0` before the first SDK invocation.

---

## [1.0.1] -- 2026-04-27

Patch release — packaging correctness, license-loading clarity, and
dashboard polish. No behavior changes to the cognitive core.

### Fixed

- **`[litellm]` extra packaging.** The extra no longer pulls in
  `sentence-transformers`. `LiteLLMAdapter` routes embeddings through
  `litellm.aembedding`, so the local embedder was never used and only
  bloated the install. Tightened to `litellm>=1.50` to match the
  shipped wheel.
- **`[dashboard]` extra now resolves.** Replaced the placeholder
  `wisdom-layer-dashboard>=1.0` dependency (no such package on PyPI)
  with the real runtime deps: `fastapi>=0.115`,
  `uvicorn[standard]>=0.30`, `websockets>=13`.
- **CLI tools no longer fall back to placeholder license literals.**
  `wisdom-layer-dashboard` and `wisdom-layer-mcp` previously defaulted
  to the strings `"wl_pro_dashboard"` / `"wl_pro_mcp"` when
  `WISDOM_LAYER_LICENSE` was unset; both now default to empty,
  yielding a clean anonymous-Free session.

### Added

- `wisdom-layer-dashboard` console script — `pip install
  "wisdom-layer[dashboard]"` now installs both the dashboard module
  and its launcher.
- New [`docs/dashboard.md`](./docs/dashboard.md) — full launch and
  configuration guide for the web dashboard.
- Quickstart "Setting Your License Key" section explaining that the
  SDK does not auto-load `.env` and showing the three supported
  patterns (shell export, sourced `.env`, `python-dotenv`).
- Troubleshooting entry for "Dashboard runs in anonymous tier even
  though I have a Pro key" (license env var not visible to the
  dashboard process).
- Pro-tier callout on the directives step of the quickstart —
  `directives.add()` and `promote()` require Pro; reading directives
  works on Free.
- LiteLLM example: explicit "`embedding_model=` is required" note,
  chat/embedder pairing table including a local Ollama row, and a
  warning about pointing `embedding_model` at a chat model
  (similarity scores compress).
- Dashboard UI: favicon, plus tier-restriction lock states on the
  cost and trajectory widgets so Free-tier users see a clear gate
  instead of silent empty panels.

### Changed

- Examples and `docs/config.md` standardized on the `backend=` keyword
  in `WisdomAgent(...)`. The legacy `storage=` alias remains
  supported and is documented in the API reference.

---

## [1.0.0] -- 2026-04-25

Initial public release.

The Wisdom Layer SDK gives LLM agents persistent, evolving memory:
multi-tier semantic recall, self-authored behavioral directives,
autonomous reflection cycles, provenance tracking, and cost
visibility. SQLite or PostgreSQL backends; Anthropic, OpenAI,
Gemini, Ollama, and LiteLLM adapters; LangGraph and MCP integrations.

See the [README](./README.md) and [docs](./docs/) for full feature
coverage, quickstarts, and the API reference.
