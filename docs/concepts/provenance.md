# Provenance

Provenance is the agent's append-only audit trail. Every mutation to
memories, directives, and facts writes a row that records what
happened, when, who initiated it, and which entities were involved.
You can ask, for any object the agent owns, "where did this come
from?" and get a deterministic answer.

---

## What gets tracked

In v1.0, provenance records three explicit links:

1. **Memory → directive** — when a directive cites the memories that
   support it (e.g., "promoted after recurring pattern in cycle X").
2. **Directive → critic review** — when a critic review references
   the directives it evaluated against.
3. **Fact → source memory** — every persisted fact carries
   `source_memory_id` so the agent can produce an audit trail for any
   claim it later makes.

Beyond those links, every mutation operation appends a row with:

- timestamp
- operation (e.g., `directive.promoted`, `memory.captured`)
- actor (agent / human / dream phase)
- entity ids involved

---

## What is **not** tracked

- **Raw LLM token streams.** The captured memory carries the prompt
  and response; provenance carries the operation, not the model
  internals.
- **Full conversation transcripts beyond Tier 1.** Tier 1 memory
  *is* the transcript; provenance does not duplicate it.
- **Recursive cross-entity graph resolution.** v1.0 records the
  three direct link types above. Walking, say, "show me every fact
  that supports every directive that flagged this critic review"
  requires the caller to traverse the chain manually. Native graph
  resolution is on the v1.1 roadmap.

---

## Access tiers

Three methods, three tiers:

| Method | Tier | Returns |
|---|---|---|
| `agent.provenance.trace(entity_id)` | Pro+ | Operation history for one entity, newest first. |
| `agent.provenance.explain(entity_id)` | Enterprise | Walks the chain and returns a human-readable rationale ("this directive was promoted on 2026-04-21 because Critic flag X recurred 4× in cycle Y"). |
| `agent.provenance.export(...)` | Enterprise | CSV/JSON dump for compliance archival. |

Free tier callers can still see basic stats (memory counts, directive
counts), but the operation history is gated.

---

## Why this matters

Closed-loop cognitive systems can drift silently — a directive that
emerged from a single bad day can keep flagging good responses for
weeks if no one can trace where it came from. Provenance is the
mechanism that lets an operator answer:

- "Why did the critic block this response?" → trace the review →
  see the directives it cited → see the memories those directives
  emerged from.
- "Where did this fact come from?" → `list_for_memory(source_id)`
  enumerates every claim a single capture produced.
- "What changed in this directive's history?" → `trace(directive_id)`
  shows promotion, reinforcement, and decay events in order.

---

## Further Reading

- [The Critic](critic.md) — the system whose evaluations provenance most often explains.
- [Directives](directives.md) — the lifecycle events that fill the audit trail.
- [API Reference](../api-reference.md) — `agent.provenance`.
