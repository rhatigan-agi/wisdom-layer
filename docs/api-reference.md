# API Reference

Complete reference for the Wisdom Layer SDK public surface. Everything
documented here is re-exported from `wisdom_layer/__init__.py` and
subject to semantic versioning stability guarantees.

## Tier annotations

Every method below is one of:

- **(Free)** — works on any tier, including the anonymous Free tier.
- **(Pro+)** — requires a Pro or Enterprise license key (`wl_pro_…` or `wl_ent_…`).
- **(Enterprise)** — requires an Enterprise license key (`wl_ent_…`).

Calling a higher-tier method on a lower-tier key raises
`TierRestrictionError` at runtime. Read-only directive inspection
(`active`, `all`, `get`, `relevant`) is intentionally Free so lapsed
Pro users can still inspect what their agent already knows.

Methods without an explicit annotation are Free.

---

## Core

### `WisdomAgent`

The primary entry point. Accepts a backend, LLM adapter, config, and
optional clock.

```python
from wisdom_layer import WisdomAgent

agent = WisdomAgent(
    agent_id: str | None = None,      # Stable tenancy identifier (or use name=)
    name: str | None = None,          # Shortcut: sets config.name and agent_id
    config: AgentConfig | None = None,# Defaults to AgentConfig.for_dev()
    llm: BaseLLMAdapter = ...,        # Required (alias: model=)
    backend: BaseBackend | None = None,# Defaults to in-memory SQLite (alias: storage=)
    clock: Clock | None = None,       # Defaults to SystemClock()
    budget_guard: BudgetGuard | None = None,
)
```

**Key methods:**

| Method | Returns | Description |
|---|---|---|
| `await agent.initialize()` | `None` | Run migrations, validate config, eagerly warm the LLM adapter (loads the local embedder for cloud adapters), emit `agent.initialized` |
| `await agent.close()` | `None` | Cancel scheduler, close backend, emit `agent.closed` |
| `await agent.status()` | `dict` | Runtime capability snapshot |
| `await agent.status_display()` | `str` | Human-readable terminal output |
| `await agent.health()` | `HealthReport` | Cognitive health (`wisdom_score` populated on Pro+) |
| `await agent.clone(new_agent_id)` | `WisdomAgent` | Deep-copy to new identity |
| `agent.on(event, handler)` | `SubscriptionToken` | Subscribe to a named event. Returns a token usable with `agent.off()`. |
| `agent.off(token)` | `None` | Unsubscribe a previously registered handler. |

**Attributes:**

| Attribute | Type | Description |
|---|---|---|
| `agent.agent_id` | `str` | Stable tenancy identifier set at construction. Every memory, directive, proposal, and dream cycle is scoped to this value. |
| `agent.name` | `str` | Configured agent name (`config.name`). |
| `agent.tier` | `Tier` | Current license tier (`Tier.FREE`, `Tier.PRO`, `Tier.ENTERPRISE`). |

**Sub-interfaces:**

| Attribute | Interface | Description |
|---|---|---|
| `agent.memory` | `MemoryInterface` | Capture, search, delete, export/import |
| `agent.directives` | `DirectivesInterface` | Add, promote, deactivate, relevant |
| `agent.critic` | `Critic` | Evaluate, audit, entropy |
| `agent.journals` | `JournalsInterface` | Write, synthesize, history |
| `agent.dreams` | `DreamsInterface` | Trigger, schedule, estimate_cost |
| `agent.provenance` | `ProvenanceInterface` | Trace, explain, export |
| `agent.facts` | `FactsInterface` | Extract, search, list_for_subject, verify_claim *(Beta — Pro+, opt-in)* |
| `agent.cost` | `CostInterface` | Summary, estimate_dream, export |

### `SyncWisdomAgent`

Blocking facade over `WisdomAgent` for scripts, Jupyter, and sync frameworks.
Same interface, blocking calls.

```python
from wisdom_layer import SyncWisdomAgent

with SyncWisdomAgent(name="demo", llm=model, backend=backend) as agent:
    agent.initialize()
    agent.memory.capture("conversation", {"text": "hello"})
```

---

## Memory

### `agent.memory.capture(event_type: str, content: dict, *, emotional_intensity: float = 0.0, created_at: datetime | None = None)`

Store a memory with automatic embedding, dedup, and salience scoring.

- `emotional_intensity: float` — Optional emotional weight (0.0–1.0).
  The only human-input lever; the SDK derives final salience from this
  plus recency, reinforcement, and access patterns.
- `created_at: datetime | None` — **New in v1.1.0.** Optional timestamp
  override. `None` (default) stamps with the agent's clock now — the
  expected path for live captures. Set this **only when importing
  historical data** with preserved timestamps; passing it for live
  capture corrupts the temporal model and breaks recency-weighted
  retrieval and dream-cycle lookback windows. Must be timezone-aware
  (UTC recommended), in the past, and within the last 10 years. Naive,
  future, or >10-years-old timestamps raise `ValueError`. Pairs with
  [`dreams.trigger(lookback_days=...)`](#agentdreamstriggerphasesnonelookbackdaysnone--pro)
  for historical-import flows.

**Returns:** `str` (memory_id)

### `agent.memory.search(query, *, limit=5, min_salience=0.0, kinds=None)`

Semantic search across all memory tiers. Ranks by cosine similarity + recency + salience.

`kinds` is an optional list of `event_type` values to restrict the
search to (e.g., `["reconsolidated_insight"]` to surface only
dream-cycle insights, or `["conversation"]` for raw events). `None`
(default) returns all kinds. Passing an explicit value also disables
the [`AgentConfig.search_insight_ratio`](#agentconfig) reservation
described below — when the caller is steering retrieval explicitly,
the SDK honors that choice.

When `AgentConfig.search_insight_ratio > 0` and `kinds` is `None`,
a fraction of the result slots is reserved for
`reconsolidated_insight` rows (dream-cycle outputs) so distilled
knowledge surfaces alongside raw events even when raw events out-rank
insights on similarity alone.

**Returns:** `list[dict[str, object]]` — each entry contains:

| Key | Type | Description |
|---|---|---|
| `id` | `str` | Memory id |
| `tier` | `str` | `raw` / `consolidated` / `reflective` (the `MemoryTier` enum value — the README's "Stream / Index / Journal" naming is the conceptual layer) |
| `event_type` | `str` | The event type used at capture |
| `content` | `dict` | The captured payload |
| `salience` | `float` | Current salience score |
| `similarity` | `float` | Cosine similarity to the query |
| `created_at` | `str` | ISO 8601 timestamp |

### `agent.memory.delete(memory_id)`

Single-row hard delete. Idempotent. Emits `memory.deleted`.

**Returns:** `DeleteReport`

### `agent.memory.delete_session(session_id)`

Session-scoped hard delete. Emits `memory.session_deleted`.

**Returns:** `DeleteReport`

### `agent.memory.delete_all()`

Full erasure of all data for this agent (all tiers + sessions +
provenance). Idempotent. Emits `memory.agent_deleted`.

**Returns:** `DeleteReport` with per-table deletion counts.

### `agent.memory.export(*, redact_embeddings=False, include_session_memories=True, tier_filter=None, redact=None, include_provenance=False, output_format="json")`

Export memories as a portable bundle.

**Returns:** `dict[str, object]`

### `agent.memory.import_(data, *, re_embed=False, mode="append")`

Import a memory bundle. Modes: `"append"`, `"replace"`, `"merge"`.

**Returns:** `dict[str, object]` with import counts and any per-row errors.

### `agent.memory.reembed(*, batch_size=100)`

Async generator that re-embeds memories with stale embeddings. Yields
progress dicts for monitoring.

### `agent.memory.forget_subject(subject_id)`

GDPR Article 17: delete all memories containing a subject.

**Returns:** `{"deleted_count": int, "memory_ids": list[str]}`

### `agent.memory.export_subject(subject_id)`

GDPR Articles 15/20: export all memories containing a subject.

---

## Directives

Read methods (`get`, `active`, `all`, `relevant`) are **(Free)**. Mutation
methods (`add`, `promote`, `deactivate`, `reinforce`) require **(Pro+)**.

### `agent.directives.add(text)` — **(Pro+)**

Add a behavioral directive. The behavior depends on
`LockConfig.directive_evolution_mode`:

- **`"active"`** (the default) — creates a directive immediately with
  `status="provisional"`. The new directive is what `relevant()` /
  `active()` / `all()` will surface.
- **`"advisory"`** — does not write a directive. Files a proposal that
  must be promoted via `directives.approve(proposal_id)` before it
  becomes a real directive.
- **`"locked"`** — raises `DirectiveLockedError`.

`directive_evolution_mode` (a `LockConfig` setting) and
`DirectiveStatus` (the per-directive lifecycle field) are independent:
the mode controls *whether* mutations apply directly; the status
describes *where* a directive sits in the provisional → active →
permanent lifecycle. A freshly-added directive in `"active"` mode
starts at `status="provisional"` and is promoted by `reinforce()` then
`promote()`.

**Returns:** `dict[str, object]` keyed by mode:

- active mode  → `{"id", "directive_id", "status"}`
- advisory mode → `{"id", "proposal_id", "mode", "action"}`

`result["id"]` is the canonical key in both modes.

### `agent.directives.get(directive_id)` — **(Free)**

Fetch a single directive by ID.

**Returns:** `dict[str, object] | None`

### `agent.directives.active()` — **(Free)**

List all non-inactive directives (provisional, active, permanent).

**Returns:** `list[dict[str, object]]`

### `agent.directives.all()` — **(Free)**

List every directive, including inactive ones.

**Returns:** `list[dict[str, object]]`

### `agent.directives.relevant(query, *, limit=5, min_similarity=0.0, track_usage=True)` — **(Free)**

Find directives relevant to a query, ranked by cosine similarity.
Inactive directives are excluded; permanent, active, and provisional
directives all participate.

- `min_similarity` — floor for the cosine similarity score. Results
  below this are dropped. `0.0` (default) disables the filter
  entirely (preserves legacy behavior — even weakly or anti-similar
  matches are returned). Recommended values are in the 0.40–0.50
  range for tighter relevance gating; `0.45` is the value used by
  `compose_context()`.
- `track_usage` — when `True` (default) and the agent has the
  `directive_evolution` feature in `active` mode, `usage_count` is
  fire-and-forget incremented for every returned directive. This
  ensures the directive lifecycle (provisional → active → permanent)
  advances as directives are retrieved, without the consumer having
  to call `reinforce()` explicitly. Auto-tracking silently no-ops on
  Free tier or in `advisory` / `locked` modes — those callers see
  purely read-only behavior. Set `track_usage=False` for
  deterministic counter behavior in tests.

**Returns:** `list[dict[str, object]]`

### `agent.directives.compose_context(query, *, limit=5, min_similarity=0.45, track_usage=True)` — **(Free)**

Build a structured prompt fragment for the current query using the
Hybrid Directive Retrieval pattern. Permanent directives
are always included (they encode the agent's stable identity), and
active / provisional directives are relevance-filtered against
`query` (they encode evolving guidance). Provisional directives are
explicitly labeled in the returned text so the LLM weights them
differently from active ones.

The returned `text` block is ready to splice into a system prompt;
the structured lists are also returned for callers that want to
render their own format. Auto-tracking semantics match `relevant()`
— every directive included in the returned block has its
`usage_count` bumped fire-and-forget when `track_usage=True` and the
tier / mode permit. (`relevant()` is called internally with
`track_usage=False` to avoid double-counting.)

**Returns:** `dict[str, object]` with keys:

| Key | Type | Description |
|---|---|---|
| `text` | `str` | Formatted block ready to inject into a system prompt. May contain up to three labeled sections: "Core directives (always apply)", "Contextual directives (relevant to this query)", "Provisional directives (under review — apply only if clearly relevant)". |
| `permanent` | `list[dict]` | Permanent directives, each with `id`, `text`, `status`. |
| `contextual` | `list[dict]` | Active directives matching `query`, each with `id`, `text`, `status`, `similarity`. |
| `provisional` | `list[dict]` | Provisional directives matching `query`, each with `id`, `text`, `status`, `similarity`. |
| `all_ids` | `list[str]` | Every directive id included in the block, in render order. |

### `agent.directives.promote(directive_id)` — **(Pro+)**

Promote a provisional directive to active.

### `agent.directives.deactivate(directive_id)` — **(Pro+)**

Deactivate a directive.

### `agent.directives.reinforce(directive_ids)` — **(Pro+)**

Increment usage counters for directives that were used in a turn.
Takes a `list[str]` of directive IDs.

---

## Critic

### `agent.critic.evaluate(output, *, context=None)` — **(Pro+)**

Evaluate agent output against active directives.

**Returns:** `dict[str, object]` (a `CriticReview`-shaped payload) with
`risk_level`, `pass_through`, and `flags`.

### `agent.critic.audit()` — **(Pro+)**

Full coherence audit across all directives. Read-only — never mutates
directives, never creates proposals.

**Returns:** `dict[str, object]` (an `AuditReport`-shaped payload).

### `agent.critic.verify_grounding(output)` — **(Pro+, Beta, opt-in)**

> **Beta surface.** Public signature subject to refinement in v1.0.x
> based on real-world usage. Reaches stable status in v1.1, after
> which standard stability guarantees apply.

Extract atomic claims from a draft response and verify each against the
agent's stored facts. Gated on the `grounding_verifier` feature.

**Returns:** `dict[str, object]` with `grounding_score` (float, 0–1),
`claim_count`, and three lists (`verified`, `unverified`,
`contradicted`) of claim/fact pairs with their match types
(`exact`, `substring`, `contradicts`, `unknown`). Each per-claim
entry also carries `match_source` (`"exact"`, `"semantic"`, or
`None`) and `similarity` (cosine score for semantic hits; `None`
otherwise) so callers can drill from "verified 8/10" down to
"6 exact, 2 semantic". The report aggregates this split as
`verified_exact_count` and `verified_semantic_count`.

When `AdminDefaults.critic_verifies_grounding=True`, `evaluate()` runs
this pass automatically and merges the result into its return payload
under `grounding`. Any contradiction promotes `risk_level` to `"high"`
and forces `pass_through=False`.

---

## Facts — **(Pro+, Beta, opt-in)**

> **Beta surface.** Public signatures of `agent.facts.*` are subject to
> refinement in v1.0.x based on real-world usage. Reaches stable status
> in v1.1, after which standard stability guarantees apply.

Atomic fact extraction at memory-write and structured lookup at
response-time. Activated by `AdminDefaults.enable_fact_extraction=True`;
defaults off so existing integrations see no behaviour change. Facts
are stored as `(subject, attribute, value)` triples with provenance
back to the source memory. v1.0 uses last-write-wins on
`(agent_id, subject, attribute)`; reconciliation, decay, and history
queries are deferred to v1.0.1.

### `agent.facts.extract(memory_id)`

Extract facts from a single memory on-demand. Same path the background
subscriber uses when `enable_fact_extraction=True`.

**Returns:** `list[dict]` — each entry has `id`, `subject`, `attribute`,
`value`, `confidence`, `source_memory_id`, `created_at`.

### `agent.facts.search(query, *, limit=5)`

Free-text search over stored facts.

**Returns:** `list[dict]` (same shape as `extract`).

### `agent.facts.list_for_subject(subject, *, limit=50)`

All facts for one entity, newest first.

### `agent.facts.list_for_memory(memory_id)`

All facts derived from one source memory (provenance lookup).

### `agent.facts.export_subject(subject)`

Audit-trail export for one entity — facts plus their source memories.

### `agent.facts.verify_claim(subject, attribute, expected_value)`

Direct claim check. Two-pass lookup: first an exact-attribute scan
against the subject's facts (Pass 1, zero embedding cost), then a
semantic fallback through `agent.facts.search` when Pass 1 misses.
The fallback exists because the fact extractor and the claim
extractor — two independent LLM calls — routinely invent different
attribute names for the same fact (e.g. `charged_amount` vs
`duplicate_charge_amount`). Without it, those facts silently fail
to verify and grounding scores are systematically depressed.

The semantic candidate is accepted when its cosine similarity meets
`AdminDefaults.grounding_semantic_threshold` (default `0.60`) and its
subject shares a case-insensitive substring with the requested
subject. The latter guard prevents location-dominated embeddings from
verifying claims about the wrong person. Set the threshold to `1.0`
or above to disable the semantic fallback entirely.

**Returns:** `dict[str, object]` with `verified` (bool), `match_type`
(one of `exact`, `substring`, `contradicts`, `unknown`),
`stored_value` (`str | None`), `source_memory_id` (`str | None`),
`match_source` (`"exact"`, `"semantic"`, or `None` for unknowns),
and `similarity` (float for semantic hits; `None` for exact hits and
unknowns).

---

## Dreams

### `agent.dreams.trigger(*, phases=None, lookback_days=None)` — **(Pro+)**

Run a dream cycle. Steps run in fixed order: `reconsolidate` →
`evolve_directives` → `critic_audit` → `directive_decay` →
`journal_synthesis`. A failure in one step is recorded but does not
abort the remaining steps.

> **New in v1.1.0:** `phases=` and `lookback_days=` are 1.1.0
> additions. Pre-1.1.0 callers used `trigger()` with no arguments and
> got the full five-step cycle every time; that call form still works
> and still runs all five steps. The new keyword-only parameters give
> Pro+ callers two new levers — phase subset selection (run only the
> steps you need) and reconsolidation lookback bounding (cap LLM cost
> on agents with deep history).

**Parameters (keyword-only):**

- `phases: Sequence[str] | None` — Optional subset of step names to
  run, in the fixed order above. Valid names: `"reconsolidate"`,
  `"evolve_directives"`, `"critic_audit"`, `"directive_decay"`,
  `"journal_synthesis"`. `None` (default) runs all five. Use this for
  lightweight passes — e.g. `phases=["reconsolidate"]` to consolidate
  raw memories without spending on directive evolution or journal
  synthesis. An empty sequence raises `ValueError`; an unknown name
  raises `ValueError` listing the valid set.
- `lookback_days: int | None` — Optional time window restricting which
  raw memories the `reconsolidate` step considers. `None` (default)
  preserves prior behavior — no time filter; consolidation ranks by
  reinforcement and salience over all candidates. Set this when you
  want the cycle to attend only to recent activity to bound LLM cost,
  or when importing historical data whose `created_at` was preserved.
  No-op for steps other than `reconsolidate`. Mirrors the parameter on
  `estimate_cost`. Non-positive values raise `ValueError`.

**Returns:** `dict[str, object]` with `cycle_id`, `started_at`,
`completed_at`, `duration_ms`, `status` (`"success"` / `"partial"` /
`"failed"`), `summary` (multi-line narrative), `steps`, `cost_breakdown`
(per-phase cost dicts), `total_tokens`, `total_usd`, and
`total_duration_ms`.

Each step dict contains `step_index`, `name`, `status`, `duration_ms`,
`error`, `reason` (set for skipped steps), and `result` (step-specific
payload — e.g. `result["created"]` is the count of newly-added
directives from `evolve_directives`).

### `agent.dreams.schedule(*, interval_hours, at=None, ignore_budget=False)` — **(Pro+)**

Register a recurring dream cycle. BudgetGuard-aware. All parameters
are keyword-only.

**Returns:** `ScheduleStatus`

### `agent.dreams.pause()` / `agent.dreams.resume()` / `agent.dreams.unschedule()` — **(Pro+)**

Lifecycle controls for scheduled dreams. Each returns `ScheduleStatus`.

### `agent.dreams.estimate_cost(*, depth=None, lookback_days=14)` — **(Pro+)**

Pre-flight cost estimate for the next dream cycle. Keyword-only.

**Returns:** `CostEstimate`

### `agent.dreams.get(cycle_id)` — **(Pro+)**

Retrieve a single dream report by 12-char hex `cycle_id`.

**Returns:** `dict[str, object] | None`

---

## Provenance

### `agent.provenance.trace(entity_id, *, limit=200)` — **(Pro+)**

Append-only event chain touching an entity, oldest first.

**Returns:** `list[dict[str, object]]`

### `agent.provenance.explain(entity_id, *, limit=200)` — **(Enterprise)**

LLM-narrated chain explanation. Memoized by event sequence hash.

**Returns:** `dict[str, object]`

### `agent.provenance.export(*, since=None, until=None, limit=500)` — **(Enterprise)**

Time-windowed provenance dump as JSON bundle.

**Returns:** `dict[str, object]`

---

## Health

`agent.health` is a callable interface — `await agent.health()` returns
the current report; `agent.health.trajectory(...)` and
`agent.health.capture_snapshot()` are attributes on the same object.

### `await agent.health()` — **(Free)**

**Returns:** `HealthReport` with:
- `wisdom_score: float` (0.0–1.0, populated on **Pro+** only — Free
  returns `0.0` and `cognitive_health="unknown"`)
- `cognitive_health: str` (`healthy` / `stagnant` / `drifting` / `overloaded`, **Pro+** only)
- `memory_stats: MemoryStats`
- `directive_stats: DirectiveStats`
- `dream_stats: DreamStats`
- `cost_stats: CostStats`

### `agent.health.trajectory(days=30)` — **(Pro+)**

Time-series of daily health snapshots. Missing days are omitted (not
zero-filled). Ordered ascending by date.

**Returns:** `list[HealthReport]`

### `agent.health.capture_snapshot()` — **(Pro+)**

Write current report to `health_snapshots`, overwriting any existing
snapshot for the same calendar day. Emits `health.snapshot`.

**Returns:** `HealthReport`

---

## Cost

### `agent.cost.summary(window="7d")` — **(Pro+)**

Aggregate spend, tokens, and call counts. Windows: `"1d"`, `"7d"`, `"30d"`, `"all"`, or a `timedelta`.

**Returns:** `CostSummary`

### `agent.cost.estimate_dream(depth="standard", lookback_days=14)` — **(Pro+)**

Pre-flight estimate of next dream cycle cost.

**Returns:** `CostEstimate` with `confidence` (low / medium / high).

### `agent.cost.export(*, since=None, until=None)` — **(Enterprise)**

CSV dump of the cost ledger.

**Returns:** `str` (CSV)

---

## Sessions

### `agent.session(session_id=None, *, ephemeral=None, scope="long_term", ttl_hours=0)`

Async context manager for session-scoped memory. `ephemeral=True`
suppresses capture, reinforcement, and dedup-merge inside the block —
useful for one-off interactions you don't want the agent to learn from.

```python
async with agent.session(session_id="conv-42", ephemeral=True) as session:
    await session.memory.capture("context", {"note": "User mentioned London"})
```

---

## Configuration

### `AgentConfig`

| Factory | Use |
|---|---|
| `AgentConfig.for_dev()` | Local iteration |
| `AgentConfig.for_prod(name=...)` | Production |
| `AgentConfig.for_testing()` | Deterministic tests |
| `AgentConfig.template_mode(...)` | Locked production deployment |

**Notable fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `search_insight_ratio` | `float` (0.0–1.0) | `0.0` | Fraction of every `memory.search()` result slot reserved for `reconsolidated_insight` rows (dream-cycle outputs). At `0.0` (default), search is purely similarity-ordered (preserves legacy behavior). At `0.4`, two of five slots in a `limit=5` search are reserved for insights when any are available. The reservation is skipped when the caller passes an explicit `kinds=` filter. Recommended range: `0.20–0.40` when insights are sparse but high-signal. |

### `FeatureFlags`

Per-agent toggles applied **on top of** tier gating — every flag
defaults to `True`, so you only need to set them to opt **out** of
features your tier permits. Available flags:

`dreams`, `scheduled_dreams`, `reconsolidation`, `journals`,
`directives`, `critic`, `goals`, `emotional_tracking`,
`health_analytics`, `provenance`, `provenance_trace`,
`provenance_explain`, `provenance_export`, `cost_visibility`,
`cost_budget`, `cost_export`.

Disabling a flag raises `FeatureDisabledError` on the gated method —
distinct from `TierRestrictionError`, which fires when the *tier*
doesn't include the feature at all.

### `ResourceLimits`

| Factory | Use |
|---|---|
| `ResourceLimits.for_cloud()` | Generous defaults |
| `ResourceLimits.for_local()` | Workstation/laptop |
| `ResourceLimits.for_small_model()` | 7B-class models |

### `LockConfig`

Per-agent write controls. `memory_mode`: `"learning"` (default —
full read/write), `"append_only"` (capture allowed, no reinforce /
decay / delete), `"read_only"` (no writes at all). Set
`freeze_decay=True` to keep `memory_mode="learning"` but stop the
nightly decay pass.

(For per-call ephemeral behaviour, use
`agent.session(ephemeral=True)` instead.)

### `SessionConfig`

Session scoping rules.

### `AdminDefaults`

Frozen tuning profile passed to `AgentConfig` via the `admin_defaults`
keyword. The default (`AdminDefaults.balanced()`) covers most agents;
specialized agents pick an archetype factory tuned for their workload.

```python
from wisdom_layer import AdminDefaults, AgentConfig

config = AgentConfig.for_prod(
    name="researcher",
    admin_defaults=AdminDefaults.for_research(),
)
```

| Factory | Profile |
|---|---|
| `AdminDefaults.balanced()` | General-purpose. Default. |
| `AdminDefaults.for_research()` | Long retention, wider consolidation, exploratory synthesis. |
| `AdminDefaults.for_coding_assistant()` | Short half-lives, aggressive decay, tight context budget. |
| `AdminDefaults.for_strategic_advisors()` | Year-long retention, strict coherence, conservative evolution. |
| `AdminDefaults.for_lightweight_local()` | Minimized LLM calls — sized for 7B-class on-prem models. |

Customer-facing code should always pick a factory. Individual fields
on the dataclass are tuning constants (T2 admin config) — they are
reserved for internal experimentation and may change between releases.

Two fields are exceptions and form part of the public surface:
`enable_fact_extraction` and `critic_verifies_grounding`. Both default
`False` and gate the v1.0 Beta facts/grounding-verifier pair (see
[`agent.facts`](#facts--pro-beta-opt-in) and
[`agent.critic.verify_grounding`](#agentcriticverify_groundingoutput--pro-beta-opt-in)).
Compose with any factory:

```python
from dataclasses import replace

admin_defaults = replace(
    AdminDefaults.balanced(),
    enable_fact_extraction=True,
    critic_verifies_grounding=True,
)
```

### `RetryPolicy(*, max_attempts=3, initial_delay_s=1.0, max_delay_s=60.0, backoff="exponential", jitter=True)`

Drives the retry loop for idempotent LLM operations (consolidation,
journal synthesis, directive evolution). Pass via `AgentConfig`:

```python
from wisdom_layer.llm.retry import RetryPolicy

config = AgentConfig(
    name="prod",
    retry_policy=RetryPolicy(max_attempts=3),
)
```

> **Default policy (v1.1.0+).** `AgentConfig.retry_policy` defaults
> to `RetryPolicy()` (3 attempts, exponential backoff with jitter).
> Transient `LLMRateLimitError`, `LLMTimeoutError`, and `LLMServerError`
> errors retry automatically before surfacing. Pre-1.1 the default
> was `None` (no retries), which proved to be a production footgun;
> the flip in v1.1.0 is breaking-but-safer. To opt out and restore
> the v1.0 behavior, pass `retry_policy=RetryPolicy(max_attempts=1)`
> (or `retry_policy=None`, which is still accepted and means "no
> retry wrapper installed"). Side-effect calls (critic audit,
> coherence checks) are intentionally never retried regardless of
> policy.

---

## Storage

### `SQLiteBackend(path, *, embed_fn=None, embedding_model_id=None, embedding_dim=None)`

Built-in SQLite backend. Zero infrastructure.

`embed_fn`, `embedding_model_id`, and `embedding_dim` all default to `None`.
When you wire the backend into a `WisdomAgent`, `agent.initialize()` calls
`backend.bind_embedder(adapter)` which threads the LLM adapter's
`embed`, `embedding_model_id`, and `embedding_dim` into the backend
automatically — so you only configure the embedder once on the adapter.
Setting any of these explicitly opts you out of auto-binding for that
field; if the adapter then disagrees, `bind_embedder` raises
`EmbeddingConfigMismatchError` at startup before any memory is written.

### `PostgresBackend(*, dsn, min_pool_size=1, max_pool_size=10, embed_fn=None, embedding_model_id=None, embedding_dim=None, admin_defaults=None)`

Async Postgres backend with pgvector. `pip install "wisdom-layer[postgres]"`.

Same `bind_embedder` auto-wiring as SQLite. Postgres v0.6 hard-codes
`VECTOR(384)` in its initial migration, so any adapter advertising a
non-384 embedding dim is rejected with `EmbeddingConfigMismatchError`
at `agent.initialize()` — swap to a 384-dim embedder (e.g.
`all-MiniLM-L6-v2`) or use `SQLiteBackend` until parameterized-dim
Postgres ships.

```python
from wisdom_layer.storage import PostgresBackend
```

The class is safe to import without the `[postgres]` extra installed —
`asyncpg` and `pgvector` are only required when you call
`await backend.initialize()`. Constructing the backend without them
succeeds; starting it raises `ImportError` with install instructions.

### `BaseBackend`

Abstract base class for custom storage backends.

### `backend_from_url(url, **kwargs)`

URL-dispatched backend construction. Schemes: `sqlite:///`, `postgresql://`.

### `backend_from_env(var_name="WISDOM_LAYER_DATABASE_URL")`

Construct backend from environment variable.

---

## LLM Adapters

### `AnthropicAdapter(*, api_key: str, model="claude-haiku-4-5-20251001", embedding_model="all-MiniLM-L6-v2", base_url="https://api.anthropic.com")`

Claude models. `api_key` is required. The `base_url` argument is passed
through to the Anthropic SDK explicitly so the `ANTHROPIC_BASE_URL`
environment variable cannot silently re-route calls — pass a custom
`base_url=` only when you really mean to (e.g. an internal proxy).
Wisdom Layer also pins `max_retries=0` on the Anthropic client so its
`RetryPolicy` owns the entire retry loop.

### `OpenAIAdapter(*, api_key: str, model="gpt-4.1-nano", embedding_model="all-MiniLM-L6-v2")`

GPT-4/4o/o-series with native JSON mode. `api_key` is required. The
adapter pins the OpenAI SDK's `max_retries=0` so Wisdom Layer's
`RetryPolicy` owns retries.

### `GeminiAdapter(*, api_key: str, model="gemini-2.5-flash", embedding_model="all-MiniLM-L6-v2")`

Google Gemini via the `google-genai` SDK. `pip install "wisdom-layer[gemini]"`.

### `OllamaAdapter(*, model="llama3.2", base_url=None, embedding_model="all-MiniLM-L6-v2")`

Local Ollama server. `base_url` defaults to `http://localhost:11434`
and can also be set via the `OLLAMA_BASE_URL` env var. No API key
required.

### `LiteLLMAdapter(*, model: str, embedding_model: str, api_key=None, api_base=None, extra_params=None)`

Provider-prefixed model strings (`bedrock/anthropic.claude-3-sonnet`,
`azure/gpt-4`, `together_ai/...`, etc.) routed through LiteLLM. Provider
credentials resolve via the standard env vars (`AWS_*`, `AZURE_*`, ...).
`pip install "wisdom-layer[litellm]"`.

`embedding_model` is **required** — there is no cross-provider default
that works everywhere. Pass the LiteLLM model string for the embedder
that matches your generation provider (e.g. `bedrock/amazon.titan-embed-text-v2:0`,
`azure/text-embedding-3-small`, `cohere/embed-english-v3.0`).
Constructing without it raises `ConfigError`. The adapter advertises
`embedding_model_id` and `embedding_dim` for the storage backend's
`bind_embedder` so users only configure the embedder in one place.

### `CallableAdapter(*, model_id, tier, fn)`

Wrap any async callable as an LLM adapter.

### `ModelRouter(adapters)`

Route requests across multiple models by tier (`sota`, `high`, `mid`, `cheap`).

### Adapter error handling

All five adapters map vendor SDK exceptions to a typed Wisdom Layer
hierarchy so `RetryPolicy` can decide whether to retry:

| Typed error | Raised on | Retryable by `RetryPolicy` |
|---|---|---|
| `LLMRateLimitError` | 429 / vendor rate-limit | yes |
| `LLMTimeoutError` | request timeout / connection error | yes |
| `LLMServerError` | 5xx from the vendor | yes |
| `LLMAuthError` | 401 / 403 | no — fix the key |
| `LLMBadRequestError` | 400 | no — fix the request |
| `ModelAdapterError` | unmapped / configuration failure | no |

Import from `wisdom_layer.llm.errors`. Catch the typed error if you
want custom handling above the agent layer; otherwise let
`RetryPolicy` (see Configuration) drive transient retries.

---

## Testing

All importable from `wisdom_layer.testing`:

| Fixture | Description |
|---|---|
| `FakeLLMAdapter` | Deterministic LLM with canned responses (no tier-gating of its own — the agent's tier is set via the `api_key` on `AgentConfig`; pass `api_key="wl_pro_…"` or `"wl_ent_…"` to exercise Pro/Enterprise paths in tests) |
| `FakeEmbedder` | Seeded hash-based embeddings (384-dim) |
| `FrozenClock` | Controllable time with `advance()` |
| `make_agent_config()` | `AgentConfig` factory |
| `make_memory()` | `Memory` factory |
| `make_directive()` | `Directive` factory |
| `make_directive_proposal()` | `DirectiveProposal` factory |

---

## Errors

All inherit from `WisdomLayerError`:

| Error | When |
|---|---|
| `TierRestrictionError` | Feature requires higher tier |
| `FeatureDisabledError` | Feature disabled via flags |
| `AgentLockedError` | Mutation on locked agent |
| `BudgetExceededError` | Cost guard triggered |
| `CriticError` | Critic evaluation failed |
| `CriticVetoError` | Critic blocked an action |
| `DirectiveLockedError` | Directive mutation on locked agent |
| `DirectiveCapacityError` | Directive limit reached |
| `DirectiveDuplicateError` | Duplicate directive text |
| `MemoryFrozenError` | Memory write on read-only agent |
| `StorageError` | Storage backend failure |
| `EmbeddingConfigMismatchError` | Backend's bound embedder disagrees with the explicit `embed_fn` / `embedding_model_id` / `embedding_dim` passed at construction (raised by `bind_embedder` at `agent.initialize()`) |
| `BackendNotInitializedError` | Backend method called before `initialize()` (or after `close()`). Inherits `RuntimeError` for backward compat |
| `StorageBusyError` | Backend lock contention |
| `StorageIntegrityError` | Data integrity violation |
| `StorageMigrationError` | Migration failure |
| `DreamCycleError` | Dream cycle failure |
| `LLMFailureError` | LLM adapter failure |
| `LLMRateLimitError` | Vendor returned 429 / rate-limit (retryable by `RetryPolicy`) |
| `LLMTimeoutError` | Request timeout / connection error (retryable) |
| `LLMServerError` | Vendor returned 5xx (retryable) |
| `LLMAuthError` | Vendor returned 401/403 (not retryable) |
| `LLMBadRequestError` | Vendor returned 400 (not retryable) |
| `ModelAdapterError` | Adapter configuration / unmapped vendor error |
| `ModelTierUnavailableError` | No adapter for requested tier |
| `ConfigError` | Invalid configuration |
| `LicenseError` | License validation failure |
| `LicenseExpiredError` | License has expired |
| `LicenseInvalidError` | License key is invalid |
| `SessionRequiredError` | Operation requires active session |
| `ContextOverflowError` | Context exceeds limits |
| `EmbeddingDimensionMismatchError` | Embedding dimension mismatch |
| `PermissionDeniedError` | Permission check failed |
| `SnapshotExpiredError` | Snapshot has expired |
| `SyncInAsyncError` | Sync method called in async context |
| `EventHandlerQuarantinedError` | Event handler failed repeatedly |

---

## Types

| Type | Description |
|---|---|
| `Memory` | Memory object with content, tier, salience, timestamps |
| `MemorySearchResult` | Pydantic type describing the `{memory, similarity}` shape, exported for downstream typing. `agent.memory.search()` itself returns the flat `dict` shape documented in the Memory section. |
| `MemoryTier` | `raw`, `consolidated`, `reflective` |
| `Directive` | Behavioral rule with status, reinforcement count |
| `DirectiveProposal` | Pending directive awaiting promotion |
| `DirectiveStatus` | `provisional`, `active`, `permanent`, `inactive`. `promote()` on an active directive sets `status="permanent"`. Deactivation sets `status="inactive"` and emits the `directive.revoked` event. Note: the `Directive.priority` field also uses `"permanent"` / `"contextual"` as a separate axis — priority controls prompt inclusion in `compose_context()`, while status tracks lifecycle. |
| `CriticReview` | Evaluation result with risk level and flags |
| `CriticFlag` | Specific concern from critic evaluation |
| `AuditReport` | Full coherence audit result |
| `DreamReport` | Dream cycle result with summary and cost breakdown |
| `DreamPhase` | Dream cycle phase identifier |
| `HealthReport` | Health metrics with wisdom_score and classification |
| `CostSummary` | Aggregated cost over a window |
| `CostEstimate` | Pre-flight cost projection |
| `PhaseCost` | Per-phase cost in a dream cycle |
| `Reflection` | Reflection data |
| `Trajectory` | Evolution trajectory |
| `RiskLevel` | `low`, `medium`, `high`, `critical` |
| `CognitiveHealth` | Health metrics container |
| `Tier` | `free`, `pro`, `enterprise` |
| `DeleteReport` | Deletion result with audit trail |

---

## Events

Subscribe via `agent.on(event_name, handler)`; the call returns a
`SubscriptionToken` you can pass to `agent.off(token)` to unsubscribe.

### Memory Events
- `memory.captured` — new memory stored
- `memory.searched` — search executed (read-only, no provenance)
- `memory.consolidated` — memory promoted to higher tier
- `memory.deleted` — memory erased
- `memory.session_started` — session opened
- `memory.session_ended` — session closed
- `memory.session_deleted` — session memories erased
- `memory.subject_forgotten` — `forget_subject()` deleted all memories for one subject
- `memory.agent_deleted` — all agent data erased
- `memory.imported` — memories imported from bundle
- `memory.exported` — memories exported (read-only)
- `memory.reembedded` — memory re-embedded with new model

### Directive Events
- `directive.added` — new directive created
- `directive.promoted` — directive status upgraded
- `directive.revoked` — directive deactivated
- `directive.proposed` — new proposal queued
- `directive.proposal_approved` / `directive.proposal_rejected`
- `directive.evolution_completed` — evolution cycle finished
- `directive.decay_completed` — decay pass finished
- `directive.exported` / `directive.imported` / `directive.reset`
- `directive.write_blocked` — mutation refused (mode/lock/capacity)

### Dream Events
- `dream.started` / `dream.completed`
- `dream.step_completed` — individual phase finished
- `dream.scheduled.start` / `dream.scheduled.complete`
- `dream.scheduled.skipped` — budget or concurrency skip
- `dream.scheduled.failed`

### Critic Events
- `critic.review_completed` — single evaluation finished
- `critic.audit_completed` — full audit finished

### Facts Events *(Beta — Pro+, opt-in)*
- `fact.extracted` — background extractor stored one or more facts from a captured memory

### Journal Events
- `journal.written` / `journal.synthesized`

### Health Events
- `health.snapshot` — daily snapshot captured

### Budget
Budget enforcement surfaces as `BudgetExceededError` raised on the
offending call rather than as an event. Pre-flight budget checks should
go through `agent.cost.estimate_dream()` (Pro+).

### Agent Events
- `agent.initialized` / `agent.closed`
