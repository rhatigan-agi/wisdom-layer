# Integration Guide

> See `examples/` for fully runnable, up-to-date scripts.

How to integrate the Wisdom Layer SDK into your application.

## Agent Lifecycle

```python
from wisdom_layer import AgentConfig, WisdomAgent
from wisdom_layer.llm.anthropic import AnthropicAdapter
from wisdom_layer.storage import SQLiteBackend

# 1. Create (once at app startup)
llm = AnthropicAdapter(api_key=os.environ["ANTHROPIC_API_KEY"])
backend = SQLiteBackend("./agent.db")

agent = WisdomAgent(
    agent_id="support-agent-prod",
    config=AgentConfig.for_prod(
        name="Support Agent",
        api_key=os.environ["WISDOM_LAYER_LICENSE"],
    ),
    llm=llm,
    backend=backend,
)
await agent.initialize()

# 2. Use (on every request)
await agent.memory.capture(
    "conversation",
    {"user": "User asked about billing", "outcome": "answered"},
)
results = await agent.memory.search(query)

# 3. Shutdown (on app exit)
await agent.close()
```

`agent_id` is a stable tenancy key. One agent ID = one persistent identity
with its own memories, directives, and dream history.

## Sessions

Sessions scope memories to a conversation or interaction window.

```python
async with agent.session(session_id="chat-1234") as s:
    await s.memory.capture("context", {"note": "User mentioned they're in Tokyo"})
    results = await s.memory.search("user location")
```

### Ephemeral Sessions

Ephemeral sessions allow search but suppress memory writes:

```python
async with agent.session(ephemeral=True) as s:
    results = await s.memory.search("policy")  # reads work
    # s.memory.capture() would be suppressed
```

## LLM Adapters

### First-Party Adapters

```python
from wisdom_layer.llm.anthropic import AnthropicAdapter
from wisdom_layer.llm.openai import OpenAIAdapter

llm = AnthropicAdapter(api_key="sk-ant-...")
llm = OpenAIAdapter(api_key="sk-...")
```

### Custom Adapters

Wrap any callable as an LLM adapter:

```python
from wisdom_layer.llm import CallableAdapter

async def my_llm(messages, *, system="", temperature=0.7, max_tokens=4096, **kwargs):
    return {"text": "response", "input_tokens": 10, "output_tokens": 20, "cost_usd": 0.0}

llm = CallableAdapter(model_id="my-model", tier="high", fn=my_llm)
```

Or subclass `BaseLLMAdapter` for full control:

```python
from wisdom_layer.llm import BaseLLMAdapter

class MyAdapter(BaseLLMAdapter):
    async def generate(self, *, messages, system="", temperature=0.7, max_tokens=4096) -> str:
        ...

    async def embed(self, text: str) -> list[float]:
        ...
```

### Model Router

Route requests across multiple models by tier:

```python
from wisdom_layer.llm import ModelRouter

router = ModelRouter(adapters=[cheap_model, main_model, best_model])
```

## Storage Backends

### SQLite (Built-In)

Zero infrastructure. Good for development, single-node deployments, and evaluation.

```python
from wisdom_layer.storage import SQLiteBackend

backend = SQLiteBackend("./agent.db")
```

### Postgres (Pro/Enterprise)

Production-scale with pgvector for sub-10ms search at 100k+ rows:

```python
from wisdom_layer.storage import PostgresBackend

backend = PostgresBackend("postgresql://user:pw@host:5432/db")
```

### URL-Dispatched

```python
from wisdom_layer.storage import backend_from_url, backend_from_env

backend = backend_from_url("postgresql://...")
backend = backend_from_env("WISDOM_LAYER_DATABASE_URL")
```

### Custom Backends

```python
from wisdom_layer.storage import BaseBackend

class MyBackend(BaseBackend):
    async def initialize(self) -> None: ...
    async def close(self) -> None: ...
    async def store_memory(self, agent_id, memory) -> str: ...
    async def search_memories(self, agent_id, embedding, limit) -> list: ...
```

## Storage and Isolation

### Agent ID Is the Isolation Boundary

Every record in the database — memories, directives, directive proposals,
dream reports, journals — is scoped to a single `agent_id`. Queries always
filter by `agent_id`; two agents sharing the same backend **cannot** see each
other's data.

```python
backend = SQLiteBackend("./shared.db")

agent_a = WisdomAgent(agent_id="support", backend=backend, ...)
agent_b = WisdomAgent(agent_id="sales", backend=backend, ...)

# agent_a.memory.search("refund policy") will never return agent_b's memories.
```

### Multiple Agents per Database

Running multiple agents against a single database is safe and supported.
Common deployment patterns:

| Pattern | When to use |
|---|---|
| One DB per environment, multiple agents | Production multi-tenant (e.g., Postgres shared across services) |
| One DB per project, one agent | Project-scoped local development |
| One DB per agent | Maximum isolation (compliance, air-gapped systems) |

### Per-Project Isolation via Relative Paths

`SQLiteBackend("./agent.db")` resolves relative to the working directory. When
each project runs from its own directory, each gets its own database file with
no extra configuration:

```
~/project-a/agent.db   ← project A's state
~/project-b/agent.db   ← project B's state (completely independent)
```

### Tier Limits Are License-Enforced

Free-tier capacity caps (3 agents, 1,000 memories per agent, 1,500
messages per rolling 30-day window) are enforced in-process by the SDK
at construction and call time. Pro's 10-agent limit is advisory and
not technically enforced. Enterprise is uncapped. The SDK does not
gate on agent count at the storage layer — multiple agents can share a
backend regardless of tier — enforcement happens at license validation
and on the count-bearing methods (`memory.capture`, `agent.respond`,
`agent.initialize`).

See [Cap Violation Handling](#cap-violation-handling) below for the
exact exception shape.

### Data Erasure Is Per-Agent

`agent.memory.delete_all()` performs a full erasure of all data for that agent
(memories, directives, proposals, dream reports, journals) without affecting
other agents sharing the same backend. This is the GDPR Article 17
right-to-erasure path:

```python
report = await agent.memory.delete_all()
# report.counts => {"memories": 142, "directives": 8, "dream_reports": 3, ...}
```

## Configuration

See [config.md](config.md) for the full decision tree. Quick summary:

```python
AgentConfig.for_dev()            # local iteration
AgentConfig.for_prod(name=...)   # production
AgentConfig.for_testing()        # deterministic tests
AgentConfig.template_mode(...)   # locked production deployment
```

### Feature Flags

```python
from wisdom_layer import FeatureFlags

flags = FeatureFlags(
    dreams=True,
    critic=True,
    directives=True,
    health_analytics=True,
    cost_visibility=True,
    provenance=True,
    scheduled_dreams=True,
)
```

### Lock Modes

```python
from wisdom_layer import LockConfig

lock = LockConfig(
    directive_evolution_mode="locked",
    memory_mode="read_only",
    freeze_decay=True,
)
```

Or use the one-call preset:

```python
config = AgentConfig.template_mode(
    name="Production Agent",
    # template_mode is a Pro feature. Get a key at
    # https://wisdomlayer.ai/pricing.
    api_key=os.environ["WISDOM_LAYER_LICENSE"],
    directives=["Rule 1", "Rule 2"],
)
```

### Resource Limits

```python
from wisdom_layer import ResourceLimits

limits = ResourceLimits.for_local()      # workstation
limits = ResourceLimits.for_cloud()      # generous defaults
limits = ResourceLimits.for_small_model() # 7B-class models
```

## Error Handling

All SDK errors inherit from `WisdomLayerError`:

```python
from wisdom_layer import (
    WisdomLayerError,
    TierRestrictionError,
    FeatureDisabledError,
    StorageError,
    DreamCycleError,
    CriticVetoError,
    DirectiveLockedError,
    MemoryFrozenError,
    BudgetExceededError,
)

try:
    await agent.dreams.trigger()
except TierRestrictionError as e:
    print(f"Upgrade required: {e.feature} needs {e.required_tier}")
except FeatureDisabledError as e:
    print(f"Enable {e.flag_name} in feature_flags")
```

See [api-reference.md](api-reference.md) for the full error hierarchy.

### Cap Violation Handling

`TierRestrictionError` operates in **two modes** that callers should
branch on:

- **Feature gate (entitlement).** A method is unavailable on the
  current tier. `e.feature` and `e.required_tier` are set;
  `e.cap_kind is None`. Maps cleanly to HTTP **403 Forbidden**.
- **Cap violation.** A Free-tier capacity cap was hit (messages,
  memories, agents). `e.cap_kind` is set, with structured
  `e.current` / `e.limit` / `e.reset_at` / `e.upgrade_url`. Maps
  cleanly to HTTP **402 Payment Required**.

```python
from wisdom_layer import TierRestrictionError

async def handle_user_message(agent, msg):
    try:
        return await agent.respond(msg)
    except TierRestrictionError as e:
        if e.cap_kind is None:
            # Pro feature on Free tier — 403 in HTTP terms
            raise HTTPException(403, {
                "error": "tier_restriction",
                "feature": e.feature,
                "required_tier": e.required_tier,
                "upgrade_url": e.upgrade_url,
            })
        # Cap violation — 402 in HTTP terms
        raise HTTPException(402, {
            "error": "capacity_cap",
            "cap_kind": e.cap_kind,         # "messages_30d" | "memories" | "agents"
            "current": e.current,
            "limit": e.limit,
            "reset_at": e.reset_at,         # ISO-8601 UTC, or None for non-rolling caps
            "upgrade_url": e.upgrade_url,
        })
```

#### What each `cap_kind` means

| `cap_kind` | Source method | Recovery action |
|---|---|---|
| `"agents"` | `agent.initialize()` | Delete an unused agent or upgrade. Agent count is at construction time, no automatic reclaim. |
| `"memories"` | `agent.memory.capture()` | Prune existing memories (`memory.delete_all()` per-agent erases everything; targeted deletes via `memory.delete()`) or upgrade. Search and reads keep working. |
| `"messages_30d"` | `agent.respond()` | Wait until `reset_at` (rolling 30-day window) or upgrade. Memory capture and search continue working. |

The `messages_30d` counter is **per-machine**, persisted in SQLite with
WAL + busy_timeout for safe concurrent-instance behavior. Cross-machine
aggregation is deferred to a future release; if you run multiple
processes on multiple machines on Free, each machine has its own 30-day
window.

#### Surfacing the upgrade prompt

The `upgrade_url` field always points at a deep-linked signup URL on
[wisdomlayer.ai/pricing](https://wisdomlayer.ai/pricing). When you map
`TierRestrictionError` into a UI surface, prefer to:

1. Show the human-readable message (`str(e)`).
2. Render the `upgrade_url` as a primary CTA.
3. For `messages_30d`, render `reset_at` as a secondary "or wait
   until …" option so the user sees that it self-resolves.

The dashboard's **Account** page (bundled with `wisdom-layer[dashboard]`)
already does this — see [docs/dashboard.md](dashboard.md) for the
shipped UI.

## Production Patterns

### Train Then Lock

```python
# Phase 1: Training (development)
agent = WisdomAgent(
    agent_id="support-v2",
    config=AgentConfig.for_dev(
        name="Support Agent",
        # Pro features (directives, dreams) require a paid key.
        # Get one at https://wisdomlayer.ai/pricing.
        api_key=os.environ["WISDOM_LAYER_LICENSE"],
    ),
    llm=llm, backend=backend,
)
await agent.initialize()
# ... capture memories, add directives, run dream cycles ...

# Phase 2: Lock for production
prod_agent = WisdomAgent(
    agent_id="support-v2",  # Same ID = same wisdom
    config=AgentConfig.template_mode(
        name="Support Agent",
        api_key=os.environ["WISDOM_LAYER_LICENSE"],
    ),
    llm=llm, backend=backend,
)
```

### Dream Cycle Scheduling

```python
from datetime import time

# In-process scheduling (BudgetGuard-aware)
await agent.dreams.schedule(interval_hours=24, at=time(3, 0))

# Manual trigger after N interactions
if interaction_count % 100 == 0:
    await agent.dreams.trigger()

# Pre-flight cost estimate
estimate = await agent.dreams.estimate_cost()
print(f"Estimated cost: ${estimate.estimated_usd:.4f}")
```

### Event Subscriptions

```python
agent.on("memory.captured", lambda event: logger.info("New memory", extra=event))
agent.on("critic.review_completed", lambda event: logger.info("Review", extra=event))
agent.on("dream.completed", lambda event: logger.info("Dream done", extra=event))
agent.on("directive.promoted", lambda event: logger.info("Rule promoted", extra=event))
# Budget breaches surface as a `BudgetExceededError` exception, not an event.
```

### Health Monitoring

```python
health = await agent.health()
print(health.wisdom_score)       # 0.0-1.0
print(health.cognitive_health)   # healthy / stagnant / drifting / overloaded

trajectory = await agent.health.trajectory(days=30)
```

### Cost Tracking

```python
summary = await agent.cost.summary(window="7d")
print(f"${summary.total_usd:.4f} across {summary.total_tokens} tokens")

estimate = await agent.cost.estimate_dream()
print(f"Next dream: ~${estimate.estimated_usd:.4f} ({estimate.confidence})")
```

## Framework Integrations

### LangGraph

See [langgraph.md](langgraph.md) for the full guide.

```python
from wisdom_layer.integration.langgraph import WisdomRecallNode, WisdomCaptureNode

recall = WisdomRecallNode(agent)
capture = WisdomCaptureNode(agent)
```

### MCP Server

See [mcp.md](mcp.md) for the full guide.

```bash
wisdom-layer-mcp --db wisdom.db --agent-id my-agent
```

## Testing

```python
from wisdom_layer.testing import (
    FakeLLMAdapter,
    FakeEmbedder,
    FrozenClock,
    make_agent_config,
    make_memory,
)
from wisdom_layer.storage import SQLiteBackend

llm = FakeLLMAdapter()
backend = SQLiteBackend(":memory:", embed_fn=FakeEmbedder().embed)
config = make_agent_config(name="test-agent")  # defaults to a free test key

agent = WisdomAgent(
    agent_id="test",
    config=config,
    llm=llm,
    backend=backend,
    clock=FrozenClock(),
)
await agent.initialize()
```

## Next Steps

- [Quickstart](quickstart.md) -- get running in 5 minutes
- [Configuration](config.md) -- presets, archetypes, resource limits
- [API Reference](api-reference.md) -- full public surface
- [examples/](../examples/) -- runnable scripts for every use case
