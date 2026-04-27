# Quickstart Guide

> See `examples/` for fully runnable, up-to-date scripts.

Get a Wisdom Layer agent running in under 5 minutes.

## Prerequisites

- Python 3.11+
- An LLM API key (Anthropic, OpenAI, or any supported provider)
- A Wisdom Layer license key is optional. Omit `api_key` and the SDK
  runs in anonymous Free mode (capture, semantic search, directive
  view). Pro features (directive evolution, the critic, dream cycles)
  require a paid key — get one at
  [wisdomlayer.ai/pricing](https://wisdomlayer.ai/pricing).

## Install

```bash
pip install "wisdom-layer[anthropic]"
```

For local models, see [quickstart_local.py](../examples/quickstart_local.py)
which uses `CallableAdapter` to wrap any OpenAI-compatible endpoint.

## Setting Your License Key

A Wisdom Layer license unlocks Pro and Enterprise features. The SDK
reads it from process environment as `WISDOM_LAYER_LICENSE`, and you
pass that into `AgentConfig(api_key=...)`:

```python
import os
config = AgentConfig.for_dev(
    name="my-agent",
    api_key=os.environ["WISDOM_LAYER_LICENSE"],   # wl_pro_... or wl_ent_...
)
```

**The SDK does not auto-load `.env` files.** Silent `.env` loading
across projects causes hard-to-debug failures when shells get polluted
by another tool's variables, so we leave that choice to you. Pick one
of these patterns:

**Shell export** (simplest):
```bash
export WISDOM_LAYER_LICENSE=wl_pro_...
python my_agent.py
```

**Source a `.env` before launch:**
```bash
set -a && source .env && set +a
python my_agent.py
```

**Or load it in code** with [`python-dotenv`](https://pypi.org/project/python-dotenv/):
```python
from dotenv import load_dotenv
load_dotenv()  # before importing wisdom_layer
```

The same pattern applies to the bundled CLIs — `wisdom-layer-dashboard`
and `wisdom-layer-mcp` both read `WISDOM_LAYER_LICENSE` from the
process environment only.

> Skipping the license key entirely is supported: omit `api_key` (or
> pass an empty string) and the SDK runs in anonymous Free mode. Get a
> registered key at [wisdomlayer.ai/pricing](https://wisdomlayer.ai/pricing).

## Run the Example

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python examples/quickstart_cloud.py
```

This runs the full cognitive loop: capture memories, search them semantically,
add directives, evaluate output with the critic, run a dream cycle, and
inspect agent status.

## Step by Step

### 1. Wire Up

Every agent needs three things: an LLM adapter, a storage backend, and a config.

```python
from wisdom_layer import AgentConfig, WisdomAgent
from wisdom_layer.llm.anthropic import AnthropicAdapter
from wisdom_layer.storage import SQLiteBackend

model = AnthropicAdapter(api_key=os.environ["ANTHROPIC_API_KEY"])
backend = SQLiteBackend("./agent.db")

agent = WisdomAgent(
    agent_id="my-agent",
    config=AgentConfig.for_dev(name="My Agent"),
    llm=model,
    backend=backend,
)
await agent.initialize()
```

Config presets handle the defaults: `AgentConfig.for_dev()` (local iteration),
`AgentConfig.for_prod()` (production), `AgentConfig.for_testing()` (deterministic
tests with dreams disabled). Use `AgentConfig.template_mode()` for locked
production deployments. See [config.md](config.md) for the full decision tree.

`agent_id` is a stable tenancy identifier -- use something meaningful (user ID,
team slug, deployment name). The SQLite database file is created automatically
on first run. Migrations apply on `initialize()`.

> **Heads-up for production:** `AgentConfig.retry_policy` defaults to `None`,
> which means a single 429 / 5xx / timeout from the LLM vendor will surface
> immediately. For anything beyond local iteration, pass an explicit
> `retry_policy=RetryPolicy(max_attempts=3)`:
>
> ```python
> from wisdom_layer.llm.retry import RetryPolicy
>
> config = AgentConfig.for_prod(
>     name="My Agent",
>     retry_policy=RetryPolicy(max_attempts=3),
> )
> ```
>
> See [api-reference.md](api-reference.md#retrypolicymax_attempts3-initial_delay_s10-max_delay_s600-backoffexponential-jittertrue)
> for tunables.

### 2. Capture Memories

```python
memory_id = await agent.memory.capture(
    "conversation",
    {"user": "What's your refund policy for enterprise?", "outcome": "answered"},
    emotional_intensity=0.3,           # optional: 0.0-1.0
)
```

Memories are stored as Tier 1 (raw) events. The SDK embeds the content for
semantic search and assigns a salience score. Higher `emotional_intensity`
boosts salience and slows decay.

### 3. Search Memories

```python
results = await agent.memory.search("refund policy", limit=5)
for r in results:
    print(r["similarity"], r["content"])
```

Search ranks results by a weighted combination of semantic similarity, recency,
and salience.

### 4. Add Directives

Directives are behavioral rules the agent authors and follows.

```python
directive = await agent.directives.add(
    "Acknowledge customer emotion before discussing policy."
)

active = await agent.directives.active()
relevant = await agent.directives.relevant("upset customer", limit=3)
```

For building a complete system prompt that bundles directives, relevant
memories, and known facts, use `agent.compose_system_prompt()` — it
applies the recommended framing and avoids the "strategy document"
failure mode where naive prompts make the model describe its approach
instead of producing the response itself:

```python
system_prompt = await agent.compose_system_prompt(
    role="customer support agent",
    query=user_message,
)
resp = await llm.messages.create(
    system=system_prompt,
    messages=[{"role": "user", "content": user_message}],
)
```

The `role` is free-form — pass `"code reviewer"`, `"research assistant"`,
or anything else; the helper stays task-neutral. Use `extra_instructions=...`
to layer task-specific guidance on top (e.g.
`"Respond as a markdown report with sections."`).

If you only need the directives + facts block (not the full prompt),
`agent.directives.compose_context()` returns the same retrieval text
as a fragment you can splice into your own prompt:

```python
ctx = await agent.directives.compose_context("upset customer", limit=3)
system_prompt = f"You are a support agent.\n\n{ctx['text']}"
```

New directives start as `provisional` and can be promoted to `active` or
`permanent`. Directives that go unused decay automatically during dream cycles.

### 5. Critic Evaluation

The critic evaluates agent output against active directives and flags risks.

```python
review = await agent.critic.evaluate(
    "Here is our return policy. Ship the item back within 14 days.",
    context={"situation": "customer is upset about a broken product"},
)

print(review["risk_level"])    # "low", "medium", "high", "critical"
print(review["pass_through"])  # True if safe to send
print(review["flags"])         # List of specific concerns
```

### 6. Dream Cycles

Dream cycles are autonomous maintenance -- reconsolidate memories, audit
directives, run decay, and synthesize journals.

```python
report = await agent.dreams.trigger()
print(report["status"])   # "success" / "partial" / "failed"
for step in report["steps"]:
    print(step["name"], step["status"])
```

In production, schedule dream cycles:

```python
await agent.dreams.schedule(interval_hours=24, at=time(3, 0))
```

Or trigger manually after N interactions. The SDK's scheduler is in-process
and BudgetGuard-aware.

### 7. Health and Cost

```python
health = await agent.health()
print(health.wisdom_score)        # 0.0-1.0
print(health.cognitive_health)    # healthy / stagnant / drifting / overloaded

cost = await agent.cost.summary(window="7d")
print(cost.total_usd, cost.total_tokens)
```

### 8. Agent Status

```python
display = await agent.status_display()
print(display)
```

## Sync API

For Jupyter notebooks, scripts, or sync frameworks, use `SyncWisdomAgent`:

```python
from wisdom_layer import SyncWisdomAgent

with SyncWisdomAgent(name="my-agent", llm=model, backend=backend) as agent:
    agent.initialize()
    agent.memory.capture("conversation", {"text": "hello"})
    results = agent.memory.search("greeting", limit=5)
    health = agent.health()
```

`SyncWisdomAgent` wraps the async API -- same methods, blocking calls. Owns
a dedicated background event-loop thread so calls are safe from Jupyter.
All calls block; no `await` is needed.

## Next Steps

- [Integration Guide](integration-guide.md) -- sessions, lock modes, production patterns
- [Configuration](config.md) -- presets, archetypes, resource limits
- [LangGraph](langgraph.md) -- 4 drop-in nodes for LangGraph agents
- [MCP Server](mcp.md) -- expose agent to Claude Code and Cursor
- [API Reference](api-reference.md) -- full public surface reference
- [examples/quickstart_cloud.py](../examples/quickstart_cloud.py) -- Anthropic cloud quickstart
- [examples/quickstart_local.py](../examples/quickstart_local.py) -- local / self-hosted models
- [examples/langgraph_quickstart.py](../examples/langgraph_quickstart.py) -- LangGraph integration
- [examples/claude_agent_sdk_quickstart.py](../examples/claude_agent_sdk_quickstart.py) -- Claude Agent SDK
- [examples/mcp_quickstart.py](../examples/mcp_quickstart.py) -- MCP server setup
