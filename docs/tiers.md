# License Tiers — Feature Matrix

This page is the **canonical record** of what every Wisdom Layer license
tier unlocks. The internal feature gate (`_internal/feature_gate.py`,
ships compiled) is the technical source of truth; this document mirrors
it in human-readable form.

If a feature is listed here, it is either shipping in v1.x or has a
"coming v1.next" pill next to it. If it is not listed here, it is not
promised on this tier.

For pricing, see [wisdomlayer.ai/pricing](https://wisdomlayer.ai/pricing).
For the deferred-features roadmap, see the public CHANGELOG.

---

## At a glance

| Capability | **Free** | **Pro** | **Enterprise** |
|---|---|---|---|
| Agent identity & lifecycle | Yes | Yes | Yes |
| Tier 1 memory (raw events) | Yes | Yes | Yes |
| Tier 2/3 memory (consolidation, reflection) | — | Yes | Yes |
| Basic search (keyword + filters) | Yes | Yes | Yes |
| Semantic search (vector embeddings) | — | Yes | Yes |
| Directive view (read-only) | Yes | Yes | Yes |
| Directive evolution (Critic-authored, lifecycle) | — | Yes | Yes |
| Critic enforcement | — | Yes | Yes |
| Atomic fact extraction (Beta, opt-in) | — | Yes | Yes |
| Critic grounding verifier (Beta, opt-in) | — | Yes | Yes |
| Dream cycles (manual + scheduled) | — | Yes | Yes |
| Custom dream phases (plugin steps) | — | — | Yes |
| Provenance — `trace` | — | Yes | Yes |
| Provenance — `explain` & `export` | — | — | Yes |
| Health analytics — basic stats | Yes | Yes | Yes |
| Health analytics — `wisdom_score` + 30-day trajectory | — | Yes | Yes |
| Health analytics — unlimited trajectory window | — | — | Yes |
| Cost visibility (summary + per-cycle estimate) | — | Yes | Yes |
| Cost CSV export | — | — | Yes |
| Multi-LLM router (route across adapters by tier) | — | Yes | Yes |
| Multi-agent mesh (shared pool, A2A comms) | — | — | Yes |
| Cross-agent memory | — | — | Yes |
| Cross-agent dream cycles | — | — | Yes |
| Storage backends | SQLite | SQLite + Postgres | Any (custom adapters) |
| **Agent count** | **3 (hard cap)** | **10 (advisory)** | **Unlimited** |
| **Memories per agent** | **1,000 (hard cap)** | **Unlimited** | **Unlimited** |
| **Messages / 30-day rolling** | **1,500 (hard cap)** | **Unlimited** | **Unlimited** |
| Telemetry default | Opt-out (anonymous counts) | Off (opt-in) | Off (opt-in) |
| Support | Docs + community | Email (~48hr) | SLA + advisory (5–10hr/mo) |
| **Price** | **$0** | **$99/mo (Pro) · $249/mo (Team)** | **Starts at $24K/yr — contact sales** |

Free includes a **14-day full Pro trial** on signup. See [Trial](#trial-14-day-pro).

---

## Free — "Try the loop"

Generous enough to build something real. Limited enough that
production-shape usage forces an upgrade conversation.

**Capabilities:**

- Agent identity and lifecycle
- Tier 1 memory (raw event capture)
- Basic search (keyword + simple filters, no embeddings)
- Directive view (read-only) — ship a curated rule set, mutation requires Pro
- Basic health stats (memory count, agent count, simple metrics)
- SQLite storage backend
- One LLM adapter at a time (Anthropic OR OpenAI OR a callable, no router)

**Capacity caps (hard-enforced):**

- **3 agents.** Independent agents only — no shared memory pool, no
  inter-agent messaging. (For multi-agent coordination, see Enterprise.)
- **1,000 memories per agent.** Once hit, capture stops until pruned or
  upgraded.
- **1,500 messages per 30-day rolling window.** This is the cap that
  creates the "agent stops compounding" moment during real use.
- **No on-demand dream cycles.** One weekly auto-cycle if scheduled.

When you hit a cap, the SDK raises `TierRestrictionError` with
structured fields you can branch on (`cap_kind`, `current`, `limit`,
`reset_at`, `upgrade_url`). The dashboard's **Account** page shows
live usage against each cap with warning banners as you approach the
threshold.

**Telemetry:** Opt-out, anonymous counts only. See [docs/telemetry.md](telemetry.md)
for the full payload schema. `WL_TELEMETRY=0` disables.

**Use rights:** Personal projects, evaluation, learning, internal
exploration. **Not licensed for commercial production deployment** —
see [License scope](#license-scope-pro-vs-enterprise).

---

## Trial — 14-day Pro

Every new Free signup includes a **14-day full Pro trial**. No credit
card. Unlock the cognitive substrate, build something real, decide.

**While in trial:**

- All Pro features active (semantic search, dream cycles, directive
  evolution, critic, fact extraction, grounding verifier, provenance
  trace, cost visibility, multi-LLM router, Postgres backend).
- All Free caps **lifted** for the duration of the trial.
- Telemetry follows Pro defaults (off by default; opt-in via
  `WL_TELEMETRY=1`).
- The dashboard's Account page shows a countdown until expiry.

**At expiry:**

- The license downgrades to its `tier_at_expiry` claim, which is
  `free` for trial signups.
- Free caps re-engage immediately. Existing data is preserved; new
  captures count against the Free message cap.
- Pro features start raising `TierRestrictionError` again.

The trial is implemented as **stateless JWT claims** (`trial_ends_at`
+ `tier_at_expiry`) — the SDK compares to its clock on every check;
no re-issuance is needed at expiry. Convert before expiry and the
cognitive history you built carries forward unchanged into Pro.

---

## Pro — "Run the loop"

**Pricing:** **$99/mo** (single seat) · **$249/mo Team** (up to 5 seats).

The full cognitive substrate for engineering teams running agents in
production. Priced for individual developers and small teams.

**Everything in Free, plus:**

**Memory and learning:**

- Tier 2 memory (consolidated, indexed)
- Tier 3 memory (journals, narrative reflection)
- Semantic search (vector embeddings)
- Reinforcement on retrieval, configurable decay policies
- Atomic fact extraction (Beta, opt-in via `AdminDefaults.enable_fact_extraction`)

**Reflection and critic:**

- Critic enforcement (output evaluation against directives)
- Directive evolution (Critic-authored, full lifecycle)
- Critic grounding verifier (Beta, opt-in via `AdminDefaults.critic_verifies_grounding`)
- Dream cycles (manual + scheduled)
- Reflection on outcomes feeds directive reinforcement

**Storage and integration:**

- Postgres backend (production-scale, pgvector)
- Multi-LLM router (route across Anthropic / OpenAI / Callable by tier)
- All shipped framework integrations (LangGraph, MCP, Claude Agent SDK,
  OpenAI Agents SDK)

**Observability:**

- Provenance trace (audit any decision back to source memories)
- `wisdom_score` health metric with 30-day trajectory
- Cost visibility (summary + per-cycle estimate)
- BudgetGuard with hard-enforced spend ceilings

**Capacity:**

- 10 agents (advisory soft cap, not technically enforced)
- Unlimited memories
- Unlimited messages
- On-demand and scheduled dream cycles

**Telemetry:** Off by default. Opt-in via `WL_TELEMETRY=1`. Pro
customers buy privacy.

**Use rights:** Internal tools and production systems your team
operates. **Not licensed for customer-facing or multi-tenant
deployments** — those require Enterprise. See
[License scope](#license-scope-pro-vs-enterprise).

**Support:** Email (~48hr response) + private Discord channel.

---

## Enterprise — "Operate the loop at scale"

**Pricing:** **Starts at $24K/yr — contact sales.** Custom-priced based
on use case, deployment shape, and seat count.

For teams running Wisdom Layer in customer-facing products, multi-tenant
deployments, or regulated environments.

**Everything in Pro, plus:**

**Multi-agent coordination:**

- Multi-agent mesh (shared memory pools, agent-to-agent messaging)
- Cross-agent memory with scoped access (private/shared/global)
- Inter-agent perspective layer (per-agent framing of shared events)
- Cross-agent critic (catch contradictions across the agent graph)
- Voting and proposal subsystem with domain-authority weighting

**Advanced reflection:**

- Cross-agent dream cycles (org-level reflection)
- Custom dream phases (define your own consolidation steps)
- Conflict surfacing with structured mediation
- Goal hierarchy and alignment tracking

**Compliance and governance:**

- Provenance explain (narrated reasoning chains)
- Provenance export (compliance archival)
- Unlimited health trajectory window
- Cost CSV export
- GDPR Article 17 deletion primitives (already in core, contractually
  backed at Enterprise)

**Storage and deployment:**

- Any storage backend (custom adapters)
- Multi-tenant deployment patterns
- White-label and OEM rights
- Optional self-hosted dashboard

**Capacity:** Unlimited everything.

**Telemetry:** Off by default. Optional opt-in. Audit-log surface for
compliance customers.

**Use rights:** Customer-facing, multi-tenant, embedded deployments.
Agents shipped inside products sold to third parties. Agents serving as
the product itself. White-label and OEM use.

**Support:** SLA-backed (response times negotiated per contract),
5–10 hours/month advisory, direct founder access for strategic
questions, quarterly architecture review.

---

## Free has independent agents, not a mesh

Free supports up to **3 independent agents**. Multi-agent coordination,
shared memory pools, inter-agent messaging, cross-agent critic, and
cross-agent dream cycles all require **Enterprise**. On Free, three
agents means three isolated cognitive contexts that do not communicate.

If a Free user calls a multi-agent primitive, the SDK raises
`TierRestrictionError(feature='multi_agent_mesh')` with the deep link
to Enterprise contact-sales.

---

## License scope (Pro vs Enterprise)

The technical feature gate distinguishes Free / Pro / Enterprise on what
methods you can call (see the matrix above — Pro is feature-limited
relative to Enterprise). **Use rights** are a separate, contractual
layer on top of that.

- **Pro** is intended for **internal tools and production systems** —
  agents your team operates and your team interacts with.
- **Customer-facing, multi-tenant, or embedded deployments** (one agent
  per end-user, agents shipped inside a product sold to third parties,
  or agents serving as the product itself to your customers) require an
  **Enterprise license**.

This boundary is contractual, not technical. The SDK does not gate you
mid-cycle on agent count or deployment shape; the expectation is that
teams operating at scale graduate to Enterprise voluntarily — usually
because they need multi-tenant deployments, custom dream phases,
provenance export, or SLA-backed support, all of which are
Enterprise-tier capabilities.

If you are unsure whether your deployment fits Pro or Enterprise, email
[jeff@rhatigan.ai](mailto:jeff@rhatigan.ai) with a one-paragraph
description of the use case.

---

## Internal feature keys

These are the exact strings the SDK's compiled feature gate checks. Tool
authors and integrators may use them when building tier-aware UI; they
are stable across v1.x.

### Free
- `agent_identity`
- `tier1_memory`
- `basic_search`
- `basic_stats`
- `directive_view`

### Pro (adds to Free)
- `tier2_memory`, `tier3_memory`
- `semantic_search`
- `dream_cycles`, `scheduled_dreams`
- `critic`
- `directive_evolution`
- `standard_analytics`
- `provenance`, `provenance_trace`
- `cost_visibility`, `cost_budget`
- `fact_extraction` — Beta, opt-in via `AdminDefaults.enable_fact_extraction`
- `grounding_verifier` — Beta, opt-in via `AdminDefaults.critic_verifies_grounding`
- `multi_llm_router`
- `postgres_backend`

### Enterprise (adds to Pro)
- `advanced_analytics` — unlimited trajectory window
- `provenance_explain`, `provenance_export`
- `cost_export`
- `multi_agent_mesh`
- `cross_agent_memory`
- `cross_agent_dreams`
- `cross_agent_critic`
- `custom_dream_phases`
- `multi_tier_routing` — internal forward gate, not user-facing in v1.x
- `license_audit_log` — license-event audit trail (forward-declared;
  no-op surface until first compliance customer requests it)

---

## How enforcement works

### Compiled feature gate

The authoritative `tier → feature` map lives in
`wisdom_layer/_internal/feature_gate.py`, which ships as a
Cython-compiled `.so` in release wheels. The Python-source
`license.TIER_FEATURES` dict is a **read-only introspection view** —
mutating it at runtime does not bypass the compiled gate. Every gated
method on `WisdomAgent` calls `_require_feature(name, min_tier)` on
entry; failure raises `TierRestrictionError`.

### What you see when gated

`TierRestrictionError` operates in two modes:

**Feature gate (HTTP-403-equivalent).** Free-tier access to a Pro
feature:

```
'dream_cycles' requires the Pro tier. Dream cycles consolidate raw
memories into durable insights between sessions, the way sleep does
for humans. Upgrade at https://wisdomlayer.ai/signup?tier=pro
```

The exception carries `feature` and `required_tier` attributes.

**Cap violation (HTTP-402-equivalent).** Free-tier hitting the message,
memory, or agent cap:

```
Throughput is throttled until 2026-05-29T00:00Z. The Free tier allows
1,500 messages every 30 days; you are at 1,512. Upgrade for unlimited
messages: https://wisdomlayer.ai/signup?tier=pro
```

The exception carries structured fields you can branch on:

| Attribute | Type | Meaning |
|---|---|---|
| `cap_kind` | `"messages_30d"` / `"memories"` / `"agents"` | Which cap. |
| `current` | int | Current usage. |
| `limit` | int | Cap value. |
| `reset_at` | ISO-8601 \| None | When the rolling window rolls over (messages only). |
| `upgrade_url` | string | Deep-linked signup URL. |

Frameworks that surface SDK errors as HTTP responses can map
`cap_kind is None` → 403 (entitlement) and `cap_kind is not None`
→ 402 (payment required).

### Signed tier claims

Tier is read from a locally-verified Ed25519-signed JWT
(`wl_<prefix>_<jwt>`). Forging a tier requires the Wisdom Layer private
signing key; the public key ships embedded in the compiled wheel.
Trial expiry is encoded in the JWT itself (`trial_ends_at` +
`tier_at_expiry` claims) — there is no server round-trip at expiry.

Legacy random-hex keys (`wl_<prefix>_<hex>`) still validate against the
licensing API with a 72-hour offline grace; this path will be retired
once all pre-v1.0 keys have rotated.

### Anonymous Free tier

Users who construct a `WisdomAgent` without an API key receive
`Tier.FREE` automatically. The SDK logs a one-time `INFO`-level
registration nudge pointing to `/signup` — this is advisory, not a
wall. Anonymous Free users get full Free-tier features and hit the
same caps as licensed Free users.

### Telemetry

The Free tier sends opt-out anonymous usage telemetry — counts only,
no content, no PII. Pro and Enterprise are silent by default. Full
disclosure, including the exact payload schema and how to disable, is
in [docs/telemetry.md](telemetry.md).

---

## Reporting a mismatch

If a feature is listed in your contract or on
[wisdomlayer.ai](https://wisdomlayer.ai) but `_require_feature` rejects
it on a key your tier should cover, that is a packaging bug — please
report it via [jeff@rhatigan.ai](mailto:jeff@rhatigan.ai)
with your `key_id` (the `kid` claim in your JWT, never the full token).
