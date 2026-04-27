# OpenClaw Integration Pattern

> **Status: Reference pattern.** This page describes how to wire Wisdom
> Layer into an OpenClaw agent today, using the standalone SDK. A
> packaged OpenClaw skill (with `SKILL.md` and a tested skill directory)
> ships in v1.1.

Wisdom Layer adds three things to an OpenClaw agent:

- **Persistent memory** that survives restarts and grows over time
- **Self-evolving directives** &mdash; behavioral rules the agent updates from its own experience
- **An internal critic** that can veto or rewrite outputs before they reach the user

The integration is a thin pattern: create the agent **once** at OpenClaw
service startup, then call into it on every turn.

## Install

```bash
pip install "wisdom-layer[anthropic]"
export ANTHROPIC_API_KEY=sk-ant-...
```

Swap `[anthropic]` for `[openai]`, `[gemini]`, `[ollama]`, or `[litellm]`
to use a different model provider. The SDK is model-agnostic.

## Lifecycle &mdash; create once, persist across runs

The agent owns a database and an LLM adapter. Build it at service startup
and reuse it across every OpenClaw turn. The `agent_id` is your stable
tenancy key &mdash; pick one and never change it.

```python
import os
from wisdom_layer import WisdomAgent, AgentConfig
from wisdom_layer.storage.sqlite import SQLiteBackend
from wisdom_layer.llm.anthropic import AnthropicAdapter

llm = AnthropicAdapter(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    model="claude-sonnet-4-6",
)

# Persist to disk so memories and directives survive restarts.
backend = SQLiteBackend("./wisdom.db", embed_fn=llm.embed)

agent = WisdomAgent(
    agent_id="my-claw-prod",                              # stable tenancy key
    config=AgentConfig.for_prod(name="OpenClaw-Wisdom"),
    llm=llm,
    backend=backend,
)

await agent.initialize()  # required before first use
```

Use `AgentConfig.for_dev(...)` during development for shorter dream
cycles and looser limits.

## Per-turn pattern

Three calls per turn: **retrieve** relevant context, **respond** as
normal, **capture** the interaction.

```python
async def handle_turn(user_input: str) -> str:
    # 1. Retrieve relevant memory + directives.
    memories = await agent.memory.search(user_input, limit=3)
    directives = await agent.directives.relevant(user_input, limit=3)

    wisdom_context = {
        "memories": "\n".join(m.memory.content for m in memories),
        "rules":    "\n".join(d.text for d in directives),
    }

    # 2. Generate the OpenClaw response, passing wisdom_context into
    #    your prompt template however you normally compose context.
    agent_output = await your_openclaw_response_fn(user_input, wisdom_context)

    # 3. Capture the interaction so the agent learns from it.
    await agent.memory.capture(
        event_type="interaction",
        content={"query": user_input, "response": agent_output},
    )

    return agent_output
```

### Field-access cheatsheet

| Call | Returns | How to read |
|---|---|---|
| `agent.memory.search(...)` | `list[MemorySearchResult]` | `result.memory.content` (str), `result.similarity` (float) |
| `agent.directives.relevant(...)` | `list[Directive]` | `directive.text` (str), `directive.priority` (str) |
| `agent.critic.evaluate(...)` | `CriticReview` | `review.pass_through` (bool) |

## Optional &mdash; critic veto before responding

If you want a self-check pass on outbound responses:

```python
review = await agent.critic.evaluate(agent_output, context=user_input)
if not review.pass_through:
    # Critic flagged the output. Inspect review.reason and either
    # regenerate, fall back to a safe response, or escalate to a human.
    agent_output = await regenerate_or_fallback(review)
```

## Periodic reflection

Trigger a dream cycle on a cadence (nightly, after N turns, on idle) so
the agent consolidates memories, evolves its directives, and audits its
own coherence:

```python
report = await agent.dreams.trigger()
print(f"Reconsolidated: {report.reconsolidated}, "
      f"new insights: {report.new_insights}, "
      f"directives proposed: {report.directives_proposed}")
```

You can also schedule this declaratively &mdash; see `agent.dreams.scheduler`.

## Shutdown

On OpenClaw service shutdown:

```python
await agent.close()
```

This flushes pending writes, persists the cost ledger, and gracefully
terminates any in-flight dream cycles.

## Notes

- **Memory grows.** Dream cycles consolidate and decay older memories so
  search stays fast. The default policy is sensible; tune via `AgentConfig`
  if your turn rate is unusual.
- **Directives are the moat.** The longer your agent runs, the more its
  directive set reflects what actually works for your users. Treat
  `agent.directives.list()` as inspectable behavior.
- **One database per `agent_id`.** If you need per-tenant isolation, use a
  per-tenant `agent_id` and a per-tenant SQLite path (or a single Postgres
  backend with `agent_id` as the partition key).

## See also

- [`examples/quickstart.py`](https://github.com/rhatigan-agi/wisdom-layer/blob/main/examples/quickstart.py) &mdash; the standalone quickstart this pattern is built on
- [`examples/critic_example.py`](https://github.com/rhatigan-agi/wisdom-layer/blob/main/examples/critic_example.py) &mdash; full critic veto loop
- [Tiers &amp; feature gating](./tiers.md) &mdash; what each tier unlocks
