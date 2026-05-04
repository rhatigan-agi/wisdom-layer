# Multi-Agent Quickstart

> Tier: **Enterprise**. The workspace API validates an `wl_ent_*` key at
> `Workspace.initialize()`. Free / Pro keys raise `TierRestrictionError`
> before any `workspace.db` file is created.

This walks the v1.2.0 multi-agent surface end to end: workspace setup →
agent registration → memory share → endorse / contest → team dream →
cross-agent provenance walk. The goal is a single runnable script that
exercises every major primitive in roughly 200 lines.

Requires `wisdom-layer >= 1.2.0` — the `wisdom_layer.workspace` package
and the `agent.memory.share()` / `agent.provenance.walk_xagent()` /
`agent.messages.*` surfaces did not exist in earlier releases.

For the patent-defensible architecture (why per-agent state stays
isolated even when memories cross the boundary), see
[`api-reference.md`](./api-reference.md#workspace).

## Prerequisites

- Python 3.11+
- An LLM provider (Anthropic shown; any supported provider works)
- An Enterprise license key — `WISDOM_LAYER_LICENSE=wl_ent_...`

```bash
pip install "wisdom-layer[anthropic]"
export WISDOM_LAYER_LICENSE=wl_ent_...
export ANTHROPIC_API_KEY=sk-ant-...
```

## 1. Construct the workspace

The workspace is the shared backend that holds all cross-agent state for
a deployment: the agent directory, the shared memory pool, team
insights, and the cross-agent provenance event log. Per-agent memories,
facts, directives, and journals continue to live in each agent's own
backend — the workspace stores only **back-references** to private rows
via opaque `source_memory_id` pointers.

```python
import asyncio, os
from wisdom_layer.workspace import Workspace, WorkspaceSQLiteBackend

async def main() -> None:
    backend = WorkspaceSQLiteBackend("./team.db")
    workspace = Workspace(
        workspace_id="research-pod",
        name="Research Pod",
        api_key=os.environ["WISDOM_LAYER_LICENSE"],
        backend=backend,
    )
    await workspace.initialize()
```

`initialize()` validates the license, applies pending workspace
migrations, and persists the canonical row in `workspaces`. A non-
Enterprise key raises `TierRestrictionError` *before* the SQLite file is
created — there is no "trial Pro key sneaks into a workspace" path.

## 2. Register agents

Each agent is constructed with its own license, its own backend, and its
own configuration — exactly as in the single-agent quickstart. Joining
the workspace is a separate, idempotent step.

```python
from wisdom_layer import WisdomAgent
from wisdom_layer.config import AgentConfig

async def make_agent(name: str) -> WisdomAgent:
    agent = WisdomAgent(AgentConfig.for_dev(
        name=name,
        api_key=os.environ["WISDOM_LAYER_LICENSE"],
    ))
    await agent.initialize()
    return agent

planner = await make_agent("planner")
critic  = await make_agent("critic")
writer  = await make_agent("writer")

await workspace.register_agent(planner, capabilities=["planner"])
await workspace.register_agent(critic,  capabilities=["critic"])
await workspace.register_agent(writer,  capabilities=["writer"])
```

`register_agent()` is idempotent on `(workspace_id, agent_id)`. Re-
registering replaces capabilities, refreshes `last_seen_at`, preserves
`registered_at`, and reactivates a previously archived row. The agent's
own license tier is **not** validated at registration — the workspace
owner's key is the authority for membership; per-agent feature gates
remain enforced inside each agent's own surface.

## 3. Share a memory into the pool

A shared memory is a *back-reference*, not a copy. The contributing
agent retains the only handle that can dereference its own
`source_memory_id` — compromising `team.db` never exposes the private
content behind that id.

```python
from wisdom_layer.workspace import Visibility

memory_id = await planner.memory.capture(
    "User shipped weekly Friday for 6 sprints — schedule asks should "
    "default to Friday afternoon unless they explicitly say otherwise.",
)

shared_id = await planner.memory.share(
    memory_id,
    visibility=Visibility.TEAM,
    reason="Cadence pattern likely useful to writer & critic.",
)
```

The pool derives a deterministic `shared_memory_id` from
`(contributor_id, source_memory_id)`, so re-sharing the same memory
returns the same id and the backend's `ON CONFLICT DO NOTHING` collapses
the duplicate. Visibility is `TEAM` (workspace agents) or `PUBLIC`
(workspace-wide, surfaced regardless of contributor-exclusion filters).
`PRIVATE` raises at the pool boundary — by definition a memory in the
pool is not private.

## 4. Endorse and contest

Endorsement is a *surfacing* primitive, not a vote. Each endorsement
feeds the `team_score` weighting that ranks shared memories during
synthesis. Re-endorsing by the same agent is a silent no-op.

```python
await workspace.pool.endorse(
    shared_id,
    endorsing_agent_id=writer.agent_id,
)

await workspace.pool.contest(
    shared_id,
    contesting_agent_id=critic.agent_id,
    reason="Sample size of 6 is too small to bake into a default.",
)
```

`reason=` on `contest()` is required and persisted, so reviewers can
adjudicate without chasing the contesting agent later. Disputes that
need dialogue belong in the messaging surface (§ 6), not the contention
audit.

Both methods emit cross-agent provenance events
(`MEMORY_ENDORSED` / `MEMORY_CONTESTED`) into the workspace log so
provenance walks can reconstruct the social graph behind any team
insight.

### Reading the pool — list vs search

Two surfaces for reading peer contributions out of the pool:

```python
# Chronological peer recency (recommended for natural-language flows in v1.2.0)
peers = await workspace.pool.list(
    exclude_contributor_id=critic.agent_id,   # everyone except the asking agent
    limit=20,
)

# Substring search (literal token match, ranked by team_score)
hits = await workspace.pool.search(
    "schedule cadence",                        # tokens must appear literally
    asking_agent_id=critic.agent_id,
    exclude_own=True,
)
```

> **`pool.search` is substring-only in v1.2.0.** It matches literal
> tokens against `SharedMemory.content` and ranks by `team_score`
> descending. A natural-language query that does not share vocabulary
> with the captured turns (e.g. *"how is the project going?"* against a
> pool containing *"Pipeline is short $500K for Q2"*) returns zero
> results — this is the documented behaviour, not a bug. For
> semantic peer recall in v1.2.0, use `pool.list(exclude_contributor_id
> =<self>, limit=N)` to surface the most recent peer contributions and
> let the synthesiser LLM do the matching. Embedding-backed
> `pool.search` lands in v1.3.0 alongside the shared-pool embedding
> column. `agent.memory.search()` (per-agent, embedding-backed on
> Pro+) is unaffected — the asymmetry is intentional for v1.2.0 only.

## 5. Run a Team Dream cycle

`team_synthesize()` pulls cross-agent memories, runs the synthesizer
agent's LLM over them, persists a `TeamInsight`, and emits a
`TEAM_INSIGHT_DERIVED_FROM_YOU` back-pointer event into **each
contributor's per-agent provenance log** — so the contributor's own
`agent.provenance.trace()` can answer *"what team-level outcomes did my
private memory feed into?"*

```python
insight = await workspace.team_synthesize(
    synthesizer=writer,
    min_contributors=2,
    visibility_in=[Visibility.TEAM, Visibility.PUBLIC],
    pool_limit=50,
)

if insight is not None:
    print(insight.content)
```

`min_contributors` gates the LLM call — if fewer than the threshold of
distinct agents have contributed, the method returns `None` without an
LLM round-trip, no insight row, no events. The synthesis is idempotent
on the prompt hash: re-running with an identical input set returns the
existing insight rather than producing a duplicate row.

The synthesizer must already be registered to the workspace — drive-by
callers raise `ValueError`. The synthesizer's identity is part of the
dream-cycle audit trail.

## 6. Agent-to-agent messaging

Messaging is exposed as eight tool methods on `agent.messages`, designed
to be bound directly into an LLM tool-use loop:

```python
await planner.messages.send(
    to=critic.agent_id,
    content="New shared memory on cadence — please review.",
    purpose="review_request",
)

inbox = await critic.messages.check_inbox(limit=10)
for msg in inbox:
    await critic.messages.reply(
        msg.message_id,
        content="Acked — see contention I just filed.",
    )
```

The bridge auto-fills `sender_id` (the agent cannot impersonate a peer
through this surface) and `recipient_capabilities` for inbox queries
(the LLM does not pass its own capability list, so a stale local view
cannot widen the match set). For broadcasts:

```python
await planner.messages.broadcast(
    capability="critic",
    content="Sprint review at 3pm — bring grounding-failure cases.",
)
```

All eight methods (`send`, `broadcast`, `reply`, `check_inbox`,
`list_thread`, `list_agents`, `mark_read`, `close_thread`) ship as
ready-to-bind tool schemas in `wisdom_layer.workspace.WORKSPACE_TOOLS`.

## 7. Walk cross-agent provenance

`agent.provenance.walk_xagent()` returns the workspace-side terminator
of the provenance walk: the team insight, the contributing
`SharedMemory` rows, and each contribution's `source_memory_id`
back-pointer into the contributor's own backend.

```python
provenance = await writer.provenance.walk_xagent(insight.id)
print(provenance.team_insight.content)
for contribution in provenance.contributions:
    print(
        contribution.contributor_agent_id,
        contribution.shared_memory_id,
        contribution.source_memory_id,
    )
```

> **Field-name conventions across the workspace surface.** Pool rows
> (`SharedMemory`, `TeamInsight`) and the wrapper
> `TeamInsightProvenance` use short attribute names — `.id` and
> `.team_insight` respectively — while the longer `shared_memory_id`
> / `team_insight_id` names are reserved for method *parameters*
> (e.g. `pool.endorse(shared_memory_id, ...)`,
> `walk_xagent(team_insight_id)`). `ProvenanceContribution` is the one
> exception: it carries `shared_memory_id`, `contributor_agent_id`,
> and `source_memory_id` as fields because each row joins three
> distinct id namespaces and a single `.id` would be ambiguous.

**The walk does not — and cannot — dereference any `source_memory_id`.**
Only the contributing agent itself, holding a handle to its own
per-agent backend, can resolve those ids via its own
`agent.memory.get(memory_id)`. The walk surface returns ids; the
isolation invariant is enforced in the type system —
`TeamInsightProvenance` has no field that could carry private content
across the boundary.

## 8. Clean shutdown

```python
    await workspace.close()
    await planner.close()
    await critic.close()
    await writer.close()

asyncio.run(main())
```

## What's next

- **`ThreadExitPolicy`** — deterministic max-turns plus optional
  cosine-stagnation and LLM-judge convergence checks for terminating
  multi-agent threads. See [`api-reference.md`](./api-reference.md#threadexitpolicy).
- **Custom dream phases** — define your own consolidation steps. Targeted
  for v1.3.0.
- **Cross-agent dream cycles & cross-agent critic** — also v1.3.0.

For the full Enterprise surface (8 messaging methods, all 5 pool
primitives, tool schemas, provenance event types) see
[`api-reference.md`](./api-reference.md). For pricing and tier scope see
[`tiers.md`](./tiers.md).
