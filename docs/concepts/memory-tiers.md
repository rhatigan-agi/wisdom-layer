# Memory Architecture: Stream, Index, Journal

Wisdom Layer organizes every agent's memory into three tiers. Each tier
serves a different purpose, and data flows in one direction only:
**capture → index → journal**.

---

## The Three Tiers

```
Tier 1: Stream   →  raw event log         (append-only)
Tier 2: Index    →  searchable store      (vector embeddings)
Tier 3: Journal  →  narrative synthesis   (LLM-generated)
```

### Tier 1 — The Stream

Every call to `agent.memory.capture()` writes to the stream. The stream
is an append-only log of raw events: conversations, tool results,
observations, feedback. Nothing is inferred or summarized — the stream
records exactly what happened.

The stream is the ground truth. Higher tiers derive from it.

### Tier 2 — The Index

The index is the searchable layer. When you call `agent.memory.search()`,
you're querying the index. Memories in the index are embedded as vectors
(384-dimensional by default) so the agent can find semantically relevant
context even when the exact words don't match.

The index is populated from the stream during dream cycles, when the SDK
reconsolidates raw events into higher-signal, deduplicated memories.

### Tier 3 — The Journal

Journals are LLM-generated narrative reflections that the agent writes
about itself during dream cycles. A journal entry synthesizes patterns
from recent memories into a coherent narrative: what the agent learned,
what changed, what goals emerged.

Journals are read by `agent.journals.latest()` and are used internally
to inform the next dream cycle. They're the agent's long-form memory of
who it has become over time.

---

## What This Means for Builders

**Day-to-day:** you interact with Tier 1 (capture) and Tier 2 (search).

```python
# Write to Tier 1
await agent.memory.capture("conversation", {"user": ..., "assistant": ...})

# Read from Tier 2
memories = await agent.memory.search("user's product feedback", limit=5)
```

**Over time:** dream cycles promote, merge, and decay memories in Tier 2,
and write Tier 3 journal entries. You trigger these explicitly:

```python
report = await agent.dreams.trigger()
journal = await agent.journals.latest()
```

**Embedding model matters:** all three tiers use the same embedding model.
Switching embedding models after you've captured memories causes a
dimension mismatch. Pick your embedding model at project start and don't
change it. See [Troubleshooting](../troubleshooting.md#embeddingdimensionmismatcherror-on-first-search)
if you've already hit this.

---

## Tier Availability by License Tier

| Feature | Free | Pro | Enterprise |
|---------|------|-----|------------|
| Tier 1: Stream capture | ✓ | ✓ | ✓ |
| Tier 2: Index search | ✓ | ✓ | ✓ |
| Tier 3: Journal synthesis | — | ✓ | ✓ |
| Memory reconsolidation | — | ✓ | ✓ |

Free-tier agents capture and search forever. They just never sleep.

---

## Further Reading

- [Dream Cycles](dream-cycles.md) — how Tier 2 and Tier 3 are written
- [Directives](directives.md) — behavioral rules that emerge from journals
- [API Reference](../api-reference.md) — `agent.memory`, `agent.journals`
