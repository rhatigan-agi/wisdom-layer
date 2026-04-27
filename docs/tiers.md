# License Tiers — Feature Matrix

This page is the **canonical record** of what every Wisdom Layer license
tier unlocks. The internal feature gate (`_internal/feature_gate.py`,
ships compiled) is the technical source of truth; this document mirrors
it in human-readable form.

If a feature is listed here, it is either shipping in v1.0 or has a
"coming v1.1" pill next to it. If it is not listed here, it is not
promised on this tier.

For pricing, see [wisdomlayer.ai/pricing](https://wisdomlayer.ai/pricing).
For the deferred-features roadmap, see the public CHANGELOG.

---

## At a Glance

| Capability | **Free** | **Pro** | **Enterprise** |
|---|---|---|---|
| Agent identity & lifecycle | Yes | Yes | Yes |
| Tier 1 memory (raw events) | Yes | Yes | Yes |
| Tier 2/3 memory (consolidation, reflection) | — | Yes | Yes |
| Basic search | Yes | Yes | Yes |
| Semantic search (vector) | — | Yes | Yes |
| Directive view (read-only) | Yes | Yes | Yes |
| Directive evolution (Critic-authored, lifecycle) | — | Yes | Yes |
| Critic enforcement | — | Yes | Yes |
| Atomic fact extraction (Beta, opt-in) | — | Yes | Yes |
| Critic grounding verifier (Beta, opt-in) | — | Yes | Yes |
| Dream cycles (manual + scheduled) | — | Yes | Yes |
| Custom dream phases (plugin steps) | — | — | **v1.1** |
| Provenance — `trace` | — | Yes | Yes |
| Provenance — `explain` & `export` | — | — | Yes |
| Health analytics — basic stats | Yes | Yes | Yes |
| Health analytics — `wisdom_score` + 30-day trajectory | — | Yes | Yes |
| Health analytics — unlimited trajectory window | — | — | Yes |
| Cost visibility (summary + per-cycle estimate) | — | Yes | Yes |
| Cost CSV export | — | — | Yes |
| Multi-agent mesh (shared pool, agent-to-agent comms) | — | — | **v1.1** |
| Cross-agent memory | — | — | **v1.1** |
| Storage backends | SQLite | SQLite + Postgres | Any (custom adapters) |
| Agent count (advisory, backend-enforced) | 1 | 10 | Unlimited |
| Support | Docs only | Email | SLA + advisory (5hr/mo) |

**v1.1 features** are listed in your service agreement on Enterprise but
are not enforceable until the v1.1 release. Customers contracting on the
basis of these features should reference the v1.1 release notes for
delivery timing.

---

## License Scope (Pro vs Enterprise)

The technical feature gate distinguishes Free / Pro / Enterprise on what
methods you can call (see the matrix above — Pro is feature-limited
relative to Enterprise). **Use rights** are a separate, contractual layer
on top of that.

- **Pro** is intended for **internal tools and production systems** —
  agents your team operates and your team interacts with.
- **Customer-facing, multi-tenant, or embedded deployments** (one agent
  per end-user, agents shipped inside a product sold to third parties,
  or agents serving as the product itself to your customers) typically
  require an **Enterprise license**.

This boundary is contractual, not technical. The SDK does not phone
home (see *No Telemetry* below) and will not gate you mid-cycle on agent
count or deployment shape. The expectation is that teams operating at
scale graduate to Enterprise voluntarily — usually because they need
multi-tenant deployments, custom dream phases, provenance export, or
SLA-backed support, all of which are Enterprise-tier capabilities.

If you are unsure whether your deployment fits Pro or Enterprise, email
[jeff@rhatigan.ai](mailto:jeff@rhatigan.ai) with a one-paragraph
description of the use case. Founder-rate Pro pricing is available to
early teams ahead of standard pricing increases.

---

## Internal Feature Keys

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

### Enterprise (adds to Pro)
- `advanced_analytics` — unlimited trajectory window
- `provenance_explain`, `provenance_export`
- `cost_export`
- `multi_agent_mesh` — **shipping v1.1**
- `cross_agent_memory` — **shipping v1.1**
- `custom_dream_phases` — **shipping v1.1**
- `multi_tier_routing` — internal forward gate, not user-facing in v1.0

---

## How Enforcement Works

### Compiled Feature Gate

The authoritative `tier → feature` map lives in
`wisdom_layer/_internal/feature_gate.py`, which ships as a
Cython-compiled `.so` in release wheels. The Python-source
`license.TIER_FEATURES` dict is a **read-only introspection view** —
mutating it at runtime does not bypass the compiled gate. Every gated
method on `WisdomAgent` calls `_require_feature(name, min_tier)` on
entry; failure raises `TierRestrictionError`.

### What Users See When Gated

Pro and Enterprise features are enforced as **hard exceptions**, not
warnings. When a Free-tier user calls a gated method (e.g.,
`agent.dreams.trigger()`), the SDK raises `TierRestrictionError` with:

1. The feature name and required tier.
2. A one-sentence hint explaining what the feature does.
3. A deep-linked signup URL (`wisdomlayer.ai/signup?tier=pro` or
   `?tier=enterprise`).

Example exception message:

```
'dream_cycles' requires the Pro tier. Dream cycles consolidate raw
memories into durable insights between sessions, the way sleep does for
humans. Upgrade at https://wisdomlayer.ai/signup?tier=pro
```

Because these are Python exceptions, they propagate through the
caller's stack. In a framework integration (LangGraph, CrewAI, MCP
server), the exception surfaces as a tool error, API error response, or
framework-specific failure — it cannot be silently ignored without an
explicit `try/except` in the consuming code.

If a feature is available at the user's tier but disabled via
`AgentConfig.feature_flags`, the SDK raises `FeatureDisabledError`
instead (a distinct exception explaining which flag to re-enable).

### Signed Tier Claims

Tier is read from a locally-verified Ed25519-signed JWT
(`wl_<prefix>_<jwt>`). Forging a tier requires the Wisdom Layer private
signing key; the public key ships embedded in the compiled wheel.
Legacy random-hex keys (`wl_<prefix>_<hex>`) still validate against the
licensing API with a 72-hour offline grace; this path will be retired
once all pre-v1.0 keys have rotated.

### Anonymous Free Tier

Users who construct a `WisdomAgent` without an API key receive
`Tier.FREE` automatically. The SDK logs a one-time `INFO`-level
registration nudge pointing to `/signup` — this is advisory, not a
wall. Anonymous Free users get full access to Free-tier features
(`basic_search`, `directive_view`, `tier1_memory`, `basic_stats`,
`agent_identity`) and hit `TierRestrictionError` on any Pro or
Enterprise method.

### No Telemetry

The SDK does not phone home. Agent counts, request counts,
multi-tenancy patterns, and deployment scale are not visible to Wisdom
Layer. Tier graduation at scale is handled contractually, not
technically.

---

## Reporting a Mismatch

If a feature is listed in your contract or on
[wisdomlayer.ai](https://wisdomlayer.ai) but `_require_feature` rejects
it on a key your tier should cover, that is a packaging bug — please
report it via [jeff@rhatigan.ai](mailto:jeff@rhatigan.ai)
with your `key_id` (the `kid` claim in your JWT, never the full token).
