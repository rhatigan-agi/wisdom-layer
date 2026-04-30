# Changelog

All notable changes to the Wisdom Layer SDK are recorded in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
