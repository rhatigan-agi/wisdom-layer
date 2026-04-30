# Wisdom Layer SDK

Cognitive architecture for AI agents that learn, reflect, and develop wisdom
over time.

**Everyone's building agent memory. We're building agent wisdom.**

```
Your Agent Code
     ↓
Wisdom Layer SDK        ← You are here
     ↓
Any LLM (Anthropic, OpenAI, or any async callable)
     ↓
Any Storage Backend (SQLite, Postgres, bring-your-own)
```

The SDK ships as a single Python package. It runs in-process inside your
application. No sockets at import time. No content, prompts, memories, or
agent data ever leave your infrastructure. The Free tier sends a small
anonymous count-payload once a day (counts only, no content, no PII) so
we can answer real questions about adoption — full disclosure and an
opt-out flag at [docs/telemetry.md](docs/telemetry.md). Pro and
Enterprise are silent by default.

---

## Why This Isn't Another Memory Layer

> RAG retrieves context. Wisdom Layer accumulates wisdom. Memory is one of nine subsystems.

Most "agent memory" products give you a vector store and a retrieval helper.
That's an open loop: capture goes in, search comes out, the agent forgets why
either happened. Wisdom Layer closes the loop:

- **Closed-loop architecture** — captured experience flows into journals,
  journals shape directives, directives feed the critic, the critic shapes the
  next capture. Every primitive feeds the next.
- **Identity that persists** — agents have a stable genome (name, role, locked
  config, permanent directives) that survives sessions, deployments, and model
  upgrades. Experience accumulates on top of identity, not in place of it.
- **In-process, not a service** — no sidecar to deploy, no proxy to
  authenticate, no inbound ports to firewall. The cognitive layer lives inside
  your Python process. (Outbound: license validation always; on Free, an
  anonymous daily count-payload — opt out with `WL_TELEMETRY=0`.)

---

## Nature & Nurture

The architecture enforces a real distinction between what's frozen at creation
and what accumulates from experience:

| **Genome — frozen at creation** | **Lived experience — accumulates** |
|---|---|
| `agent_id`, `name`, `role` | Three-tier memory (Stream → Index → Journal) |
| `AgentConfig.template_mode()` locked deployment | Provisional → active → permanent directive lifecycle |
| `LockConfig.directive_evolution_mode="locked"` | Reinforcement on retrieval, decay from disuse |
| Permanent directives | First-person journals synthesized by dream cycles |
| The compiled `_internal/` cognitive kernel | `wisdom_score` trajectory and cognitive-state classifier |
| Tier + feature gate (Ed25519-verified) | Self-authored directives and emerged goals |

Most "agent memory" tools give you only the right column, smashed into chat
history. Wisdom Layer gives you both — and enforces the boundary.

---

## The Closed Loop

```
capture → search → consolidate → decay → directives → critic → journals → dreams
   ▲                                                                          │
   │                                                                          │
   └──── this loop is the wisdom layer — every other system is open-loop ─────┘
```

Every primitive in this loop is implemented, tested, and persisted. Dream
cycles orchestrate the maintenance operations — reconsolidation, critic audit,
directive decay, journal synthesis, goal extraction — with error isolation and
observable history.

---

## Day 1 vs. Day 90

Same query. Same agent. Different amount of accumulated experience.
*(Illustrative — see [Measured Outcomes](#measured-outcomes) below for verified results.)*

```python
# Day 1 — fresh agent, no journals, no directives
> await agent.respond("How should I handle billing escalations?")
"I'll need more context. Could you describe the situation?"

# Day 90 — 200+ conversations captured, 12 dream cycles run,
#          5 self-authored directives, 8 weekly journals
> await agent.respond("How should I handle billing escalations?")
"Three patterns matter here, based on what I've seen:
 1. Verify identity first (directive d-021, learned 2026-02-04
    after a refund-fraud incident).
 2. If the customer mentions a competitor, escalate immediately
    — those churn at 4× baseline (journal week 9).
 3. Don't quote refund amounts before reading their plan tier
    (critic flagged this in 7 reviews; promoted to permanent)."
```

The first response is what you get from any LLM. The second is the same agent,
ninety days into its own experience. That delta is the product.

---

## Measured Outcomes

**v1.0 Beta benchmark suite (April 2026), Claude Haiku 4.5 under test,
GPT-4o GEval judge, four arms (Vanilla / mem0 / Basic Memory / Wisdom
Layer):**

- **2.65× fewer fabrications than vanilla** — Wisdom Layer 0.916 vs
  Vanilla 0.346 mean Groundedness, 5 / 5 probes pass at the 0.7 threshold.
- **Perfect atomic-fact recall (10/10)** — tied with Basic Memory; mem0
  and vanilla score 0/10.
- **Independent quality audit ranks Wisdom Layer first** — composite
  7.79 vs Basic 6.17 / mem0 6.00 / Vanilla 5.50, locked pre-committed
  criteria, separate Opus 4.7 judge.
- **Self-correction & drift handling** — Critic 3/3 PASS on directive-
  adherence probes, last-write-wins drift score 1.000.

Full table, methodology disclosures, and the contested 4-arm Groundedness
result we publish anyway are at
[wisdomlayer.ai/benchmarks](https://wisdomlayer.ai/benchmarks).
Methodology files in this repository:
[fabrication & grounding](benchmarks/fabrication_eval.md) ·
[independent quality audit](benchmarks/independent_audit.md). Eval
harness, raw transcripts, and expanded suites ship in a follow-up
release.

---

## Cognitive Primitives

| Concept | What It Does |
|---|---|
| **Memory** | Three-tier storage (Stream → Index → Journal) with semantic search, salience scoring, reinforcement on retrieval, and automatic decay |
| **Directives** | Self-authored behavioral rules with provisional → active → permanent lifecycle. The agent writes the rules it lives by |
| **Critic** | Prevents drift, hallucination, and self-contradiction. Reviews output against active directives, scores risk (low / medium / high / critical), can veto |
| **Journals** | First-person reflections written by the agent itself. Journals become directives. Directives become rules the critic enforces. The loop closes |
| **Dreams** | Autonomous maintenance cycles that consolidate memory, synthesize journals, propose directives, and audit recent output — without prompting |

---

## Production Discipline

| Concept | What It Does |
|---|---|
| **Provenance** | Append-only audit trail of every mutation -- captures, directive lifecycle, dream phases, snapshots. `agent.provenance.trace()` for any entity, `.explain()` (Enterprise) for narrated chains, `.export()` (Enterprise) for compliance archival |
| **Health Trajectory** | Composite `wisdom_score` (0-1) snapshotted daily, cognitive-state classifier (healthy / stagnant / drifting / overloaded), and longitudinal trajectory: 30-day window on Pro, unlimited on Enterprise |
| **BudgetGuard** | Hard-enforced spend ceilings on three windows -- daily, monthly, per-cycle. Calls fail at the cap, not warnings in a log. Pre-flight cost estimation for dream cycles. CSV export on Enterprise |

### Trust & Enforcement

The SDK is designed to be trusted in production environments where you
cannot redeploy to fix a tier check or audit an opaque dependency.

- **Compiled Cython feature gate** -- the authoritative `tier -> feature`
  table ships as a `.so` extension. Monkeypatching the Python-source
  `license.TIER_FEATURES` view does not bypass the compiled gate.
- **Ed25519-signed license tokens** -- tier claims are verified locally
  against an embedded public key. No network round-trip per call, no
  central authority can flip a feature on or off behind your back.
- **Privacy-respecting telemetry** -- the only network traffic the SDK
  generates beyond your own LLM calls is (a) license validation against
  the licensing API and (b) on the Free tier only, an anonymous daily
  count-payload (~600 bytes) — no memory content, no prompts, no PII,
  no agent or directive text. Pro and Enterprise are silent by default
  (telemetry off; opt-in via `WL_TELEMETRY=1`). Free disables with
  `WL_TELEMETRY=0`. Full schema: [`docs/telemetry.md`](docs/telemetry.md).

Full enforcement model and per-method gate keys: [`docs/tiers.md`](docs/tiers.md).

---

## Install

```bash
pip install wisdom-layer

# With provider extras
pip install "wisdom-layer[anthropic]"
pip install "wisdom-layer[openai]"
pip install "wisdom-layer[postgres]"

# Framework integrations
pip install "wisdom-layer[langgraph]"
pip install "wisdom-layer[mcp]"
```

Runtime dependencies are intentionally minimal: `pydantic`, `aiosqlite`,
`httpx`, and `numpy` (lazy-imported). Provider adapters and integrations
are extras — a customer using `CallableAdapter` never pulls in `anthropic`
or `openai`.

---

## Quick Start

The example below walks the full closed loop — capture, reflect, enforce. On
Free tier, capture and search work standalone; the dream cycle, critic, and
journal synthesis require a Pro license.

```python
import asyncio
import os
from wisdom_layer import WisdomAgent, AgentConfig
from wisdom_layer.llm.anthropic import AnthropicAdapter
from wisdom_layer.storage import SQLiteBackend

async def main() -> None:
    agent = WisdomAgent(
        agent_id="support-agent-001",
        config=AgentConfig.for_dev(
            name="Support Agent",
            role="Customer support specialist",
            # Optional on Free tier (memory only).
            # Required for dreams, critic, directives, journals.
            api_key=os.environ.get("WISDOM_LAYER_LICENSE"),
        ),
        llm=AnthropicAdapter(api_key=os.environ["ANTHROPIC_API_KEY"]),
        backend=SQLiteBackend("./agent.db"),
    )
    await agent.initialize()

    # 1. CAPTURE — every interaction feeds the loop.
    await agent.memory.capture(
        "conversation",
        {"user": "Refund policy for enterprise?", "outcome": "answered"},
    )
    await agent.memory.capture(
        "conversation",
        {"user": "Refund denied — escalating", "outcome": "escalated"},
    )

    # 2. REFLECT — the dream cycle reconsolidates memory, synthesizes a
    #    first-person journal, and proposes new directives. (Pro+)
    report = await agent.dreams.trigger()
    print(report.insights)             # what the agent learned
    print(report.directive_proposals)  # rules the agent wrote for itself

    # 3. ENFORCE — the critic checks new output against active directives,
    #    flagging drift and contradictions before they ship. (Pro+)
    review = await agent.critic.evaluate(
        "I'd rather skip identity verification and just refund."
    )
    print(review.risk_level)  # low / medium / high / critical

    await agent.close()

asyncio.run(main())
```

For sync code, use `SyncWisdomAgent` — a blocking facade that wraps
the async API for Jupyter notebooks, scripts, and sync frameworks:

```python
from wisdom_layer import SyncWisdomAgent

with SyncWisdomAgent(name="demo", llm=model, backend=backend) as agent:
    agent.initialize()
    agent.memory.capture("conversation", {"text": "hello"})
```

See [docs/quickstart.md](docs/quickstart.md) for a step-by-step walkthrough.

---

## Surface Area

```python
WisdomAgent
+-- memory        # capture, search, delete, export/import, reembed
+-- directives    # add, promote, deactivate, relevant, decay
+-- critic        # evaluate, audit, entropy, verify_grounding (Beta)
+-- journals      # write, synthesize, candidates, history
+-- dreams        # trigger, schedule, pause, resume, estimate_cost
+-- provenance    # trace, explain, export
+-- facts         # extract, search, list_for_subject, verify_claim (Beta)
+-- health()      # wisdom_score, classification, trajectory, snapshot
+-- cost          # summary, estimate_dream, export
+-- session()     # scoped or ephemeral memory context
+-- clone()       # deep-copy agent to new identity
+-- status()      # runtime capability snapshot
+-- status_display()  # human-readable terminal output
```

**Atomic facts + grounding verifier (v1.0 Beta, opt-in).** When
`AdminDefaults.enable_fact_extraction=True`, every memory captured
on the Pro/Enterprise tier passes through a background extractor
that distills it into `(subject, attribute, value)` triples with
provenance back to the source memory. Pair with
`critic_verifies_grounding=True` to make `agent.critic.evaluate()`
extract claims from a draft response, look each one up against the
fact store, and promote risk to `high` on any contradiction. Both
toggles default off so existing users see no behavior change; the
features still cost nothing if you don't opt in.

Three-tier memory:

| Tier | Role | Owner |
|---|---|---|
| **Stream** | Raw capture -- everything that happens, append-only | `memory.capture()` |
| **Index** | Embedded, searchable, reinforced on retrieval, decays over time | `memory.search()` |
| **Journal** | Distilled narrative -- synthesized nightly by the dream cycle | `dreams.trigger()` |

Four LLM tiers, router-resolved, never named by caller:

| Tier | Use |
|---|---|
| `sota` | Dream phase 2b, goal extraction, hypothesis engine |
| `high` | Phase 2c, coherence check, audit, structured output |
| `mid` | Reconsolidation, journal synthesis |
| `cheap` | Pattern extraction, fallback summarization |

---

## LLM Adapters

Built-in adapters plus bring-your-own:

| Adapter | Install | Notes |
|---|---|---|
| `AnthropicAdapter` | `wisdom-layer[anthropic]` | Extended thinking, tool use |
| `OpenAIAdapter` | `wisdom-layer[openai]` | GPT-4/4o/o-series, native JSON mode |
| `CallableAdapter` | built-in | Wrap any async function as an LLM |

```python
from wisdom_layer.llm.anthropic import AnthropicAdapter
from wisdom_layer.llm.openai import OpenAIAdapter
from wisdom_layer.llm import CallableAdapter, ModelRouter

# Route requests across models by tier
router = ModelRouter(adapters=[cheap_model, main_model, best_model])
```

For local models (Ollama, vLLM, LM Studio), use `CallableAdapter` to wrap
any OpenAI-compatible endpoint. See [quickstart_local.py](examples/quickstart_local.py).

---

## Framework Integrations

| Framework | Install | What You Get |
|---|---|---|
| **LangGraph** | `wisdom-layer[langgraph]` | `WisdomRecallNode`, `WisdomCaptureNode`, `WisdomDreamNode`, `WisdomDirectivesNode` |
| **MCP** | `wisdom-layer[mcp]` | 7 tools + 3 resources via stdio -- works with Claude Code and Cursor |

See [docs/langgraph.md](docs/langgraph.md), [docs/mcp.md](docs/mcp.md) for integration guides.

---

## Storage Backends

| Backend | Install | Best For |
|---|---|---|
| `SQLiteBackend` | built-in | Development, single-node, free tier (~10k memories) |
| `PostgresBackend` | `wisdom-layer[postgres]` | Production, Pro/Enterprise (sub-10ms search at 100k+) |
| `BaseBackend` | built-in | Subclass for custom storage |

```python
from wisdom_layer.storage import SQLiteBackend, PostgresBackend, backend_from_url

# SQLite (zero infrastructure)
backend = SQLiteBackend("./agent.db")

# Postgres (production scale)
backend = PostgresBackend("postgresql://user:pw@host:5432/db")

# URL-dispatched
backend = backend_from_url("postgresql://...")
```

See [docs/performance.md](docs/performance.md) for storage benchmarks.

---

## Configuration

```python
from wisdom_layer import AgentConfig, FeatureFlags, ResourceLimits, LockConfig

# Presets (recommended)
AgentConfig.for_dev()                    # local iteration
AgentConfig.for_prod(name="My Agent")    # production
AgentConfig.for_testing()                # deterministic tests
AgentConfig.template_mode(...)           # locked production deployment

# Resource profiles
ResourceLimits.for_cloud()               # generous defaults
ResourceLimits.for_local()               # workstation/laptop
ResourceLimits.for_small_model()         # 7B-class models
```

Lock an agent for production in one call:

```python
import os

config = AgentConfig.template_mode(
    name="Production Bot",
    api_key=os.environ["WISDOM_LAYER_LICENSE"],  # Pro tier — https://wisdomlayer.ai/pricing
    directives=["Rule 1", "Rule 2"],
)
# -> directives locked, memory read-only, dreams off
```

See [docs/config.md](docs/config.md) for the full decision tree.

---

## Sessions and Ephemeral Memory

```python
async with agent.session(
    session_id="conv-42",
    ephemeral=True,         # nothing persists past the block
    ttl_hours=24,
) as session:
    await session.memory.capture("context", {"note": "User is in London"})
    results = await session.memory.search("user location")
```

---

## Memory Deletion (GDPR Article 17)

Three idempotent delete primitives, all single-transaction, all emitting
audit events on the CRITICAL delivery tier:

```python
report = await agent.memory.delete(memory_id)
report = await agent.memory.delete_session(session_id)
report = await agent.memory.delete_all()
```

---

## Observability

One event bus per agent. Every subsystem emits named events with versioned
payloads. Sync or async handlers, wildcard subscriptions, fire-and-forget
dispatch.

```python
agent.on("memory.captured", on_capture)
agent.on("dream.completed", on_dream_done)
agent.on("critic.review_completed", on_review)
agent.on("directive.promoted", on_new_rule)
agent.on("memory.deleted", on_erasure_audit)       # CRITICAL tier
# Budget breaches surface as a `BudgetExceededError` exception, not an event.
```

---

## Determinism and Testing

```python
from wisdom_layer.testing import (
    FakeLLMAdapter,    # Deterministic LLM responses
    FakeEmbedder,      # Deterministic embeddings
    FrozenClock,       # Controllable time
    make_agent_config, # Config factory
    make_memory,       # Memory factory
)
```

`wisdom_layer.testing/` is a **stable public surface** -- customer tests may
import from it and expect minor-version stability.

---

## License Tiers

| | **Free** | **Pro** | **Enterprise** |
|---|---|---|---|
| Memory | Tier 1 (raw) | Tier 1–3 + semantic search | Tier 1–3 + semantic search |
| Dream Cycles | — | On-demand + scheduled | + custom phases |
| Critic / Directives | View directives only | Full lifecycle + Critic | Full lifecycle + Critic |
| Provenance | — | `trace` | `trace` + `explain` + `export` |
| Health Analytics | Basic stats | `wisdom_score` + 30-day trajectory | + unlimited trajectory |
| Cost Visibility | — | Summary + estimate | + CSV export |
| Multi-Agent Mesh / cross-agent memory | — | — | Yes |
| Agents | **3 (hard cap)** | 10 (advisory) | Unlimited |
| Memories per agent | **1,000 (hard cap)** | Unlimited | Unlimited |
| Messages / 30-day rolling | **1,500 (hard cap)** | Unlimited | Unlimited |
| Storage | SQLite | Postgres + SQLite | Any (custom adapters) |
| Telemetry default | Opt-out (anonymous counts) | Off (opt-in) | Off (opt-in) |
| Support | Docs + community | Email (~48hr) | SLA + advisory |
| **Price** | **$0** | **$99/mo · Team $249/mo** | **Starts at $24K/yr — contact sales** |

**14-day full Pro trial on signup.** Every Free signup includes a 14-day
trial with all caps lifted and the full Pro substrate unlocked. No
credit card. At expiry, the license downgrades to Free and existing
data is preserved.

Free-tier capacity caps (3 agents / 1,000 memories per agent / 1,500
messages per rolling 30-day window) are **enforced in-process** by the
SDK at construction and call time — they raise structured
`TierRestrictionError` with `cap_kind`, `current`, `limit`, `reset_at`,
and `upgrade_url` fields so frameworks can branch cleanly between
"upgrade to unlock" (HTTP 403) and "you hit a usage cap" (HTTP 402).

See [docs/tiers.md](docs/tiers.md) for the canonical feature matrix
(every gated capability + internal feature keys + enforcement details).
See [wisdomlayer.ai/pricing](https://wisdomlayer.ai/pricing) for current pricing.

---

## Where to Read Next

**Getting started**

| Guide | Description |
|---|---|
| [Quickstart](docs/quickstart.md) | Get running in 5 minutes |
| [Integration Guide](docs/integration-guide.md) | Production patterns, sessions, error handling |
| [Configuration](docs/config.md) | Presets, archetypes, resource limits |
| [Troubleshooting](docs/troubleshooting.md) | Common errors, symptoms, and fixes |

**Concepts**

| Guide | Description |
|---|---|
| [Memory tiers](docs/concepts/memory-tiers.md) | Stream / Index / Journal architecture |
| [Directives](docs/concepts/directives.md) | Behavioral rules that learn and evolve |
| [Dream cycles](docs/concepts/dream-cycles.md) | The reflection pipeline |
| [The Critic](docs/concepts/critic.md) | Internal values-alignment engine |
| [Provenance](docs/concepts/provenance.md) | Append-only audit trail and the trace/explain/export tiers |

**Integrations**

| Guide | Description |
|---|---|
| [LangGraph](docs/langgraph.md) | 4 drop-in nodes for LangGraph agents |
| [MCP Server](docs/mcp.md) | Expose agent to Claude Code, Cursor, and any MCP tool |
| [Dashboard](docs/dashboard.md) | Web UI for inspecting memories, directives, dreams, and health |
| [Claude Agent SDK](docs/claude-agent-sdk.md) | Add wisdom to Anthropic Agent SDK agents |
| [OpenAI Agents SDK](docs/openai-agents-sdk.md) | Coming soon |

**Reference**

| Guide | Description |
|---|---|
| [API Reference](docs/api-reference.md) | Full public surface reference |
| [Tiers](docs/tiers.md) | Canonical per-tier feature matrix + enforcement model |
| [Performance](docs/performance.md) | Storage benchmarks (SQLite vs Postgres) |
| [Benchmarks](benchmarks/fabrication_eval.md) | v1.0 Beta fabrication & grounding evaluation methodology |
| [Independent Audit](benchmarks/independent_audit.md) | Second-judge locked-rubric quality audit |

---

## Examples

| Example | Description |
|---|---|
| [basic_agent.py](examples/basic_agent.py) | Minimal agent setup |
| [memory_example.py](examples/memory_example.py) | Memory capture, search, sessions, export |
| [critic_example.py](examples/critic_example.py) | Critic evaluation, directives, risk assessment |
| [quickstart_cloud.py](examples/quickstart_cloud.py) | Full cognitive loop (cloud) |
| [quickstart_local.py](examples/quickstart_local.py) | Local models (Ollama, vLLM, LM Studio) via `CallableAdapter` |
| [quickstart_ollama.py](examples/quickstart_ollama.py) | Native `OllamaAdapter` quickstart |
| [quickstart_litellm.py](examples/quickstart_litellm.py) | LiteLLM router (Bedrock, Azure, Cohere, Together, …) |
| [langgraph_quickstart.py](examples/langgraph_quickstart.py) | LangGraph 3-node integration |
| [claude_agent_sdk_quickstart.py](examples/claude_agent_sdk_quickstart.py) | Claude Agent SDK integration |
| [mcp_quickstart.py](examples/mcp_quickstart.py) | MCP server setup |
| [compounding_demo.py](examples/compounding_demo.py) | Multi-run improvement proof |

---

## Stability Guarantees

- **Public surface** -- everything re-exported from `wisdom_layer/__init__.py`.
  Breaking changes require a major version bump.
- **Beta surface** -- `agent.facts.*` and `agent.critic.verify_grounding()`
  are marked Beta in v1.0. Their public signatures are subject to refinement
  in v1.0.x patch releases based on real-world usage. They reach stable
  status in v1.1, after which standard stability guarantees apply. Opt-in
  only via `AdminDefaults(enable_fact_extraction=True, critic_verifies_grounding=True)`.
- **Testing surface** -- `wisdom_layer.testing/*`. Stable across minor versions.
- **Event payloads** -- every payload carries `schema_version`; adding fields
  is non-breaking, removing or renaming requires a version bump.
- **Error hierarchy** -- every public subclass of `WisdomLayerError` is stable.
- **Private surface** -- anything prefixed `_` or living under `_internal/`
  can change between any two commits. Do not import from there.

---

## Security

To report a vulnerability, email `jeff@rhatigan.ai` or use GitHub
Security Advisories. Do **not** open a public issue. Full policy in
[SECURITY.md](SECURITY.md).

---

## Contributing

Wisdom Layer is closed-source commercial software. The package source is
maintained in a private repository and is not accepting external code
contributions or pull requests at this time.

Bug reports, reproductions, and feature requests are welcome — please use
the [issue tracker](https://github.com/rhatigan-agi/wisdom-layer/issues)
and the provided templates.

---

## On the Roadmap

Per-user behavioral learning — directives that scope to specific users or
relationships, so agents get better at *this person*, not just in general.
Tracking on the public roadmap.

---

## License

Wisdom Layer is commercial software distributed under the
[Wisdom Layer Commercial License](LICENSE). One license covers all tiers --
your license key determines which features you can use at runtime.

- Install with `pip install wisdom-layer` -- same wheel for every tier
- Free tier is free to use, not free to modify or redistribute
- Full terms in [`LICENSE`](LICENSE); readable summary in [`EULA.md`](EULA.md)

Patent pending.
