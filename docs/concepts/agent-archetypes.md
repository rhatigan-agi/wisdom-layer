# Agent Archetypes

Wisdom Layer is a domain-neutral cognitive architecture. The same SDK runs
a customer support agent, a coding assistant, a strategic advisor, or a
research agent. **Archetype factories** are how you tell the SDK which
kind of workload you're running, so it can tune retention, decay,
directive lifecycle, and reflection cadence to match.

If you've read the loom-code project — Claude's persistent-memory layer
for software development — and wondered whether the same SDK that powers
that is "really" a customer-support engine that's been repurposed: it
isn't. Loom-code v2 calls `AdminDefaults.for_coding_assistant()` and
inherits zero customer-support priming.

This doc explains how that separation works.

---

## The Two Things an Archetype Tunes

An archetype changes two things and *only* two things:

1. **Numerical tuning constants** — half-lives, decay factors, directive
   volume caps, evolution temperature, context budgets. These shape *how
   long memories live, how many directives the agent can hold at once,
   and how aggressively reflection rewrites them.*
2. **Directive evolution phrasing guidance** — a single optional string
   appended to the directive-evolution prompt during dream cycles. This
   shapes *the voice and framing the agent uses when it writes new rules
   for itself.*

Everything else is shared. Memory capture, retrieval, fact extraction,
the Critic, dream-cycle phases, the directive lifecycle state machine —
all domain-neutral. The archetype is a tuning profile, not a personality
implant.

---

## Picking an Archetype

```python
from wisdom_layer import AdminDefaults
from wisdom_layer.config import AgentConfig

config = AgentConfig(
    name="my-agent",
    admin_defaults=AdminDefaults.for_coding_assistant(),
    ...
)
```

The factories that ship with the SDK:

| Factory | Designed for | Key tradeoffs |
|---|---|---|
| `AdminDefaults.balanced()` | General-purpose, exploratory builds | Default — matches pre-archetype behavior |
| `AdminDefaults.for_research()` | Long-horizon knowledge work, deep synthesis | Long retention (180-day archive), wider consolidation, higher evolve temperature |
| `AdminDefaults.for_coding_assistant()` | Dev tooling, code review, agentic coding | Short retention (60-day archive), aggressive decay, deterministic evolution, code-review phrasing |
| `AdminDefaults.for_consumer_support()` | End-user-facing service, support, coaching | User-perspective phrasing constraint; balanced retention/decay |
| `AdminDefaults.for_strategic_advisors()` | High-stakes infrequent decisions, institutional memory | Year-long retention, strict coherence, conservative evolution |
| `AdminDefaults.for_lightweight_local()` | Small models (Qwen, Phi), on-prem, budget-constrained | Trim everything — directives, journal size, context budget, single-rule-per-cycle evolution |

Pick the one closest to your workload. If none fit, start with `balanced()`
and let your usage patterns inform whether you need to switch.

---

## How Phrasing Guidance Stays Scoped

The only place an archetype injects domain-specific *language* into the
SDK is `dream_evolve_style_guidance` — a string appended as one extra
"Rules" bullet to the directive evolution prompt during a dream cycle.

The values shipped today:

```python
# for_coding_assistant
"Phrase rules as code-review heuristics with falsifiable triggers
 (e.g., 'When a function exceeds 50 lines, flag it for splitting')."

# for_consumer_support
"Phrase rules from the perspective of serving the user well, not from
 a business-strategy perspective. Avoid framing terms like 'retention',
 'lifetime value', 'loyalty', 'maximize', or 'strategically'. A rule
 the user would feel respected by, not manipulated by."
```

That's the entire surface area for archetype-driven personality. Two
consequences worth understanding:

- **A coding-assistant agent never sees customer-support framing.** The
  consumer-support guidance is not in its prompt; the SDK's directive
  evolution prompt is otherwise identical to a research or strategic
  build.
- **A consumer-support agent never sees code-review framing.** Same
  story in reverse.

If you're building in a domain that doesn't fit any shipped archetype
(red-team security, B2B sales-ops, automated trading), you can leave
`dream_evolve_style_guidance` as `None` (the `balanced()` default) — the
SDK's universal directive evolution rules are domain-neutral and will
produce reasonable rules without any guidance string. Or supply your own
phrasing constraint via a tuning override; see [Tuning Overrides](#tuning-overrides).

---

## Why This Matters for Memory Architecture

Tuning constants have outsized effects across long horizons. A few
examples:

- **Recency half-life.** `for_coding_assistant()` uses a 3-day half-life
  for recency salience (yesterday's debug session is today's noise);
  `for_research()` uses 21 days (a paper you read three weeks ago is
  still relevant); `for_strategic_advisors()` uses 30 days. Same memory
  retrieval algorithm, very different decay curves.
- **Directive volume cap.** `for_research()` allows 100 directives
  (complex domains accumulate complex rule sets); `for_lightweight_local()`
  caps at 20 (small models can't hold large rule sets in context);
  `for_coding_assistant()` sits at 40 (enough for code-review heuristics
  without overwhelming a focused agent).
- **Evolution temperature.** `for_coding_assistant()` runs at 0.1
  (deterministic, falsifiable rules); `for_research()` at 0.4
  (exploratory creative connections); `for_strategic_advisors()` at 0.15
  (rare, careful evolution).

These are tuning numbers — there is no domain-specific code path. The
same `evolve_directives` phase runs in every archetype; what changes is
how many rules it proposes per cycle, how warm the LLM samples are, and
how big the active rule set is allowed to grow.

---

## Tuning Overrides

The factory output is a frozen dataclass. For tests or unusual
deployments, use `dataclasses.replace`:

```python
from dataclasses import replace
from wisdom_layer import AdminDefaults

profile = AdminDefaults.for_coding_assistant()
profile = replace(profile, directive_max_volume=60)
```

Customer-facing code should generally stick to the shipped factories
unless you've measured a workload-specific reason to deviate. The
archetype values were tuned against that archetype's learning dynamics —
mixing fields from different archetypes is rarely better than picking
the closest archetype and living with its defaults.

---

## Designing Your Own Archetype

If you're shipping a product on top of Wisdom Layer and want a tuned
profile of your own, the recipe is:

1. Start from the shipped archetype closest to your workload.
2. Run a few weeks of real usage and inspect dream-cycle reports
   (`agent.dreams.last_report()`).
3. Identify the symptoms — directive set growing too fast / too slow,
   memories decaying before they're useful / hanging around too long,
   the Critic flagging too many contradictions, journals coming out
   thin.
4. Adjust one or two fields at a time. Document why.

The shipped archetypes themselves were built this way — they're not
prescriptive, they're starting points the SDK has been validated
against.

---

## Further Reading

- [Memory Tiers](memory-tiers.md) — what gets retained at each tier
- [Directives](directives.md) — the lifecycle that archetype tuning shapes
- [Dream Cycles](dream-cycles.md) — where `dream_evolve_style_guidance`
  is consumed
- [API Reference](../api-reference.md) — `AdminDefaults` field-level docs
