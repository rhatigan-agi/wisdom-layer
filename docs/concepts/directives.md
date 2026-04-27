# Directives

Directives are behavioral rules your agent learns from experience and
applies to future responses. They are the mechanism by which an agent
gets better at its job over time.

A directive looks like: *"When a customer expresses frustration, acknowledge
the emotion before discussing policy."*

---

## Where Directives Come From

Directives have four sources:

| Source | How |
|--------|-----|
| **Manual** | `agent.directives.add(text)` — you write the rule explicitly |
| **Dream cycle** | The agent proposes rules it inferred from recent patterns |
| **Critic** | Failure analysis produces rules from blocked/flagged responses |
| **Imported** | `agent.directives.import_(directives)` — port rules from another agent |

---

## The Directive Lifecycle

Every directive starts as provisional and earns permanence through use.

```
provisional (tuned trial window)
    │
    ├── infrequent usage during trial  →  inactive (decayed, not deleted)
    │
    └── trial elapsed                  →  active (contextual)
                                              │
                                              ├── unused for a tuned window  →  inactive
                                              │
                                              └── manually promoted          →  permanent
```

**Provisional** — newly added. The agent tries it out and sees if it fits.

**Active (contextual)** — retrieved by semantic search when relevant. Decays
if not used. Most directives live here.

**Active (permanent)** — always loaded into context regardless of the query.
Reserve permanent status for universal rules that apply to every interaction.

**Inactive** — decayed from disuse. Not deleted — available for audit via
`agent.directives.all()`.

---

## Using Directives in Prompts

For most agents, the recommended pattern is the higher-level
`agent.compose_system_prompt()` — it bundles directives, relevant
memories, and known facts into a complete system prompt with framing
that avoids the "strategy document" failure mode (where naive prompts
make the model describe its approach instead of producing the response
itself):

```python
system = await agent.compose_system_prompt(
    role="customer support agent",
    query=user_message,
)
```

If you only need the directives + facts fragment (for example, when
you're already building your own system prompt and just want to splice
the retrieval block in), use `compose_context()` directly. It implements
the Hybrid Directive Retrieval pattern — permanent rules always loaded,
active/provisional relevance-filtered, provisional explicitly labeled
as under review — and auto-tracks usage so directives advance through
their lifecycle as they're retrieved.

```python
ctx = await agent.directives.compose_context(
    "customer is angry about billing",
    limit=5,
)

system = f"""You are a support agent.

{ctx["text"]}
"""
```

`ctx["text"]` is a ready-to-splice block with up to four labeled
sections: *Core directives*, *Contextual directives*, *Provisional
directives*, and *Known facts*. Provisional rules are flagged so the
LLM weights them differently from active ones. The Known facts section
header includes a citation cue so the LLM treats the rendered
`subject / attribute: value` lines as authoritative grounding rather
than background context. The structured `permanent`, `contextual`,
`provisional`, `facts`, and `all_ids` keys are also returned for
callers that want to render their own format.

For lower-level access, `directives.relevant(query)` returns a flat
ranked list — useful when you want to merge directives with other
context sources or apply your own filtering. Pass `track_usage=False`
in tests if you need deterministic counter behavior.

```python
directives = await agent.directives.relevant(
    "customer is angry about billing",
    min_similarity=0.45,  # tighter relevance gating
)
```

---

## Locking Directives

If you've trained an agent and want to freeze its behavior for production,
set `directive_evolution_mode="locked"` on your `LockConfig`. Locked agents
still read and use directives — they just can't add new ones or let dream
cycles evolve them.

```python
from wisdom_layer.config import AgentConfig, LockConfig

config = AgentConfig(
    name="Prod Agent",
    lock=LockConfig(directive_evolution_mode="locked"),
    ...
)
```

See the [Integration Guide](../integration-guide.md) for the full
train-then-lock production pattern.

---

## Deduplication

The SDK silently deduplicates directives that are near-duplicates of the
active set, using a tuned similarity threshold. If you add a directive
that means nearly the same thing as an existing one, the existing one is
returned instead of creating a duplicate.

---

## Further Reading

- [Dream Cycles](dream-cycles.md) — how directives evolve overnight
- [The Critic](critic.md) — how directives are enforced at evaluation time
- [API Reference](../api-reference.md) — `agent.directives`
