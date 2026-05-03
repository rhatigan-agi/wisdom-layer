# Quickstart Guide

> See `examples/` for fully runnable, up-to-date scripts.

Get a Wisdom Layer agent running in under 5 minutes.

## Prerequisites

- Python 3.11+
- An LLM API key (Anthropic, OpenAI, or any supported provider)
- A Wisdom Layer license key is optional. Omit `api_key` and the SDK
  runs in anonymous Free mode (capture, basic search, directive view)
  with the Free-tier capacity caps documented below. Sign up at
  [wisdomlayer.ai/pricing](https://wisdomlayer.ai/pricing) for a free
  registered key — you also get a **14-day full Pro trial** (no card)
  with caps lifted and the full cognitive substrate unlocked.

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
> registered key at [wisdomlayer.ai/pricing](https://wisdomlayer.ai/pricing) —
> includes a 14-day full Pro trial with all caps lifted.

## Free-Tier Capacity Caps

The Free tier is generous enough to build something real. It is also
hard-capped so production-shape usage forces an upgrade conversation.
Caps are enforced in the SDK, not at a remote service:

| Cap | Limit | What happens at the cap |
|---|---|---|
| Agents | 3 | `agent.initialize()` raises `TierRestrictionError(cap_kind="agents")`. |
| Memories per agent | 1,000 | `memory.capture()` raises `TierRestrictionError(cap_kind="memories")`. Search and reads continue working. |
| Messages per 30-day rolling | 1,500 | `agent.respond()` raises `TierRestrictionError(cap_kind="messages_30d")` with a `reset_at` timestamp. |

Each cap exception carries structured fields (`cap_kind`, `current`,
`limit`, `reset_at`, `upgrade_url`) so frameworks can surface a clean
upgrade prompt rather than a generic 500.

```python
from wisdom_layer import TierRestrictionError

try:
    await agent.respond(user_message)
except TierRestrictionError as e:
    if e.cap_kind == "messages_30d":
        return f"Message cap hit. Resets at {e.reset_at}. Upgrade: {e.upgrade_url}"
    if e.cap_kind is None:
        return f"Pro feature {e.feature} required. Upgrade: {e.upgrade_url}"
    raise
```

**Trial signup lifts every cap for 14 days.** When the trial expires,
caps re-engage and existing data is preserved — message counts since
the trial-end timestamp roll into the Free message window. See
[docs/tiers.md](tiers.md#trial-14-day-pro) for the full trial mechanic.

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

> **Embeddings run locally, not via your API key.** The cloud adapters
> (`AnthropicAdapter`, `OpenAIAdapter`, `GeminiAdapter`) use
> `sentence-transformers` on your machine for vector search — your
> `api_key` only pays for generation. The embedder ships inside
> `pip install wisdom-layer[anthropic]` (and the `[openai]` / `[gemini]`
> extras); pass `embedding_model="..."` to swap models. See
> [config.md § Embeddings](config.md#embeddings) for the full surface.

Config presets handle the defaults: `AgentConfig.for_dev()` (local iteration),
`AgentConfig.for_prod()` (production), `AgentConfig.for_testing()` (deterministic
tests with dreams disabled). Use `AgentConfig.template_mode()` for locked
production deployments. See [config.md](config.md) for the full decision tree.

`agent_id` is a stable tenancy identifier -- use something meaningful (user ID,
team slug, deployment name). The SQLite database file is created automatically
on first run. Migrations apply on `initialize()`.

> **Retry policy (v1.1.0+):** `AgentConfig.retry_policy` now defaults
> to a real `RetryPolicy()` (3 attempts, exponential backoff with
> jitter) — transient `429` / `5xx` / timeout errors from the LLM
> vendor retry automatically. Tune the policy explicitly if you want
> different limits, or opt out:
>
> ```python
> from wisdom_layer.llm.retry import RetryPolicy
>
> # Tune (e.g., longer caps for batch jobs):
> config = AgentConfig.for_prod(
>     name="My Agent",
>     retry_policy=RetryPolicy(max_attempts=5, max_delay_s=900),
> )
>
> # Opt out (surface every transient error immediately):
> config = AgentConfig.for_prod(
>     name="My Agent",
>     retry_policy=RetryPolicy(max_attempts=1),
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

**Filter by event type.** Pass `kinds=` (or its alias `event_types=`) to scope
the search to one or more event-type tags — useful when retrieving session
records, dream-cycle insights, or any other tag you've captured against:

```python
# Only dream-cycle insights
insights = await agent.memory.search("policy lessons", kinds=["reconsolidated_insight"])

# Equivalent (alias)
insights = await agent.memory.search("policy lessons", event_types=["reconsolidated_insight"])

# Only raw conversations, ignore everything else
chat = await agent.memory.search("upset customer", kinds=["conversation"])
```

The same `kinds=` / `event_types=` filter is available on
`agent.memory.export()` for selective backups and migrations.

### 4. Add Directives

Directives are behavioral rules the agent authors and follows.

> **Tier note:** `directives.add()` and `promote()` require the Pro tier
> (`directive_evolution` feature). On the Free tier, directive *reading*
> works (`active()`, `relevant()`, `compose_context()`) so you can ship
> a curated rule set with your app — but mutation raises
> `TierRestrictionError`. To follow this step verbatim, set
> `WISDOM_LAYER_LICENSE` to a Pro key
> ([wisdomlayer.ai/pricing](https://wisdomlayer.ai/pricing)). Free-tier
> users can still run steps 1–3, 5 (critic), and 7–8.

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

> **Phase subsets and lookback (v1.1.0+):** `dreams.trigger()` accepts
> two new keyword-only arguments — `phases=` and `lookback_days=` —
> that let you run a subset of steps and bound the reconsolidation
> window. Useful for lightweight passes that don't need the full
> five-step cycle, or for cost control on agents with deep history.
>
> ```python
> # Cheap pass — consolidate raw memories only:
> await agent.dreams.trigger(phases=["reconsolidate"])
>
> # Bound LLM cost on a deep-history agent:
> await agent.dreams.trigger(lookback_days=14)
>
> # Audit-only pass after a critic-flagged interaction:
> await agent.dreams.trigger(phases=["critic_audit"])
> ```
>
> Calling `trigger()` with no arguments still runs all five steps —
> existing code keeps working unchanged. See
> [api-reference.md](api-reference.md#agentdreamstriggerphasesnone-lookback_daysnone--pro)
> for the full parameter contract.

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

## Multi-agent workspace (Enterprise)

Three agents share a workspace, one shares a memory, one runs a Team
Dream cycle synthesizing a team insight, and another walks the
provenance back to the contributing private memory id. Requires an
Enterprise license key.

```python
import asyncio

from wisdom_layer import WisdomAgent
from wisdom_layer.storage import SQLiteBackend
from wisdom_layer.workspace import (
    Visibility,
    Workspace,
    WorkspaceSQLiteBackend,
)

async def main() -> None:
    # 1. One workspace; three per-agent backends.
    workspace = Workspace(
        workspace_id="team-alpha",
        name="Team Alpha",
        api_key="wl_ent_…",
        backend=WorkspaceSQLiteBackend("workspace.db"),
    )
    await workspace.initialize()

    planner = WisdomAgent(
        agent_id="planner",
        llm=model,
        backend=SQLiteBackend("planner.db"),
    )
    critic = WisdomAgent(
        agent_id="critic",
        llm=model,
        backend=SQLiteBackend("critic.db"),
    )
    writer = WisdomAgent(
        agent_id="writer",
        llm=model,
        backend=SQLiteBackend("writer.db"),
    )
    for a in (planner, critic, writer):
        await a.initialize()

    await workspace.register_agent(planner, capabilities=["planner"])
    await workspace.register_agent(critic,  capabilities=["critic"])
    await workspace.register_agent(writer,  capabilities=["writer"])

    # 2. The planner discovers something useful and shares it.
    captured = await planner.memory.capture(
        "lesson",
        {"text": "Three small specs land in production faster than one big one."},
    )
    shared_id = await planner.memory.share(
        captured.memory_id,
        visibility=Visibility.TEAM,
        reason="Pattern worth other agents seeing",
    )

    # 3. The critic endorses; the workspace pool ranks it.
    await workspace.pool.endorse(
        shared_memory_id=shared_id,
        agent_id="critic",
        reason="Confirmed against past launch retros",
    )

    # 4. A Team Dream cycle synthesizes a team insight.
    insight = await workspace.pool.synthesize_team_insight(
        content="Small, well-scoped specs ship faster than monoliths.",
        contributing_shared_memory_ids=[shared_id],
        salience=0.7,
    )

    # 5. The writer walks the provenance back across the agent boundary.
    walk = await writer.provenance.walk_xagent(insight.id)
    for c in walk.contributions:
        print(
            c.contributor_id,        # "planner"
            c.shared_memory_id,      # the pool id
            c.source_memory_id,      # back-pointer into planner.db
            c.team_score,
        )
        # `c.source_memory_id` is opaque here — only the planner can
        # dereference it via planner.memory.get(c.source_memory_id).

    for a in (planner, critic, writer):
        await a.close()
    await workspace.close()


asyncio.run(main())
```

The shared pool stores back-references, never copies. The provenance
walk surfaces the contributor's `source_memory_id` so the contributing
agent can dereference it locally — but the workspace itself can never
read another agent's private memory.

LLMs reach the messaging surface via tool use:

```python
from wisdom_layer.workspace import WORKSPACE_TOOLS, execute_tool

# Stamp WORKSPACE_TOOLS into the LLM's tool list. When a tool-use
# block comes back, route it through execute_tool:
result = await execute_tool(
    agent=writer,
    name=tool_use.name,
    arguments=tool_use.input,
)
```

See [api-reference.md](api-reference.md#multi-agent-workspace--enterprise)
for the full multi-agent surface, and [tiers.md](tiers.md#enterprise--operate-the-loop-at-scale)
for what's gated behind Enterprise.

## Anonymous Telemetry

By default, Free-tier installs send a single anonymous count-payload
per day to `api.wisdomlayer.ai/v1/telemetry`: install ID, SDK version,
agent / memory / message / fact / dream-cycle / directive counts, OS,
Python major.minor. **No content. No PII. No agent names. No memory
text.** Roughly 600 bytes/day per install.

Pro and Enterprise are silent by default; telemetry is opt-in via
`WL_TELEMETRY=1` on those tiers.

Disable on Free at any time:

```bash
export WL_TELEMETRY=0
```

Full disclosure, payload schema, and retention policy:
[docs/telemetry.md](telemetry.md).

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

## Want a UI?

[Wisdom Studio](https://github.com/rhatigan-agi/wisdom-studio) is the
canonical reference application for this SDK — a forkable FastAPI + React
app with a chat surface, real-time cognition stream, side-by-side compare
mode (baseline vs. memory vs. full-wisdom), and seven env vars for shaping
kiosk / demo / embed deployments without code changes.

```bash
docker run -d -p 3000:3000 -v $HOME/.wisdom-studio:/data \
  ghcr.io/rhatigan-agi/wisdom-studio:latest
```

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
