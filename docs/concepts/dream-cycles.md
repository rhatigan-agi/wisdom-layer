# Dream Cycles

A dream cycle is Wisdom Layer's reflection pipeline — the process by
which an agent consolidates what it has experienced into lasting wisdom.
It's what separates an agent that *remembers* from an agent that actually
*learns*.

Dream cycles are a Pro and Enterprise feature. Free-tier agents capture
and search memories but do not run dream cycles.

---

## What a Dream Cycle Does

When you trigger a dream cycle, the agent runs through five main phases:

1. **Reconsolidation** — Recent memories are clustered and synthesized into
   higher-signal insights. Near-duplicates are merged. Salience scores are
   updated. Low-value memories begin to decay.

2. **Directive evolution** — The agent audits its current behavioral rules,
   proposes new rules it's inferred from experience, and retires rules that
   have become contradictory or stale.

3. **Journal synthesis** — The agent writes a narrative reflection that
   summarizes what changed: what patterns it noticed, what it learned, what
   goals emerged. This journal entry feeds into the next cycle.

4. **Goal extraction** — If strategic goals are enabled, the agent extracts
   concrete goals from the journal and updates its goal state.

5. **Decay and maintenance** — Memory scores are decayed by age and
   disuse. Expired session memories are pruned.

---

## What You Get Back

`agent.dreams.trigger()` returns a dict:

```python
report = await agent.dreams.trigger()

report["cycle_id"]          # 12-char hex id for this cycle
report["status"]            # "success" | "partial" | "failed"
report["summary"]           # multi-line human-readable narrative
report["steps"]             # list of per-step dicts (see below)
report["started_at"]        # ISO 8601 timestamp
report["completed_at"]      # ISO 8601 timestamp
report["duration_ms"]       # total wall-clock duration
report["cost_breakdown"]    # list of per-phase cost dicts
report["total_tokens"]      # int — sum across the cycle
report["total_usd"]         # float — sum across the cycle
```

Each entry in `report["steps"]` is itself a dict with `step_index`,
`name` (`"reconsolidate"` / `"evolve_directives"` / `"critic_audit"` /
`"directive_decay"` / `"journal_synthesis"`), `status`
(`"success"` / `"failed"` / `"skipped"`), `duration_ms`, `error`,
`reason` (set when a step is skipped — e.g.
`"insufficient_candidates"`), and `result` (the step-specific payload).

To pull totals out of a step (e.g. how many memories were
reconsolidated, how many directives were proposed) read the matching
`result` dict — for example `next(s["result"] for s in report["steps"]
if s["name"] == "evolve_directives")["created"]`.

---

## Triggering Dream Cycles

**Manually** — call `agent.dreams.trigger()` directly. Useful after a
batch of interactions or at the end of a demo.

**Scheduled** — set a recurring schedule so the agent reflects overnight:

```python
from datetime import time

await agent.dreams.schedule(interval_hours=24, at=time(3, 0))
```

The agent will run a dream cycle at 3 AM every day. Cancel with
`await agent.dreams.unschedule()`. (`pause()` / `resume()` are also
available if you only want to halt the schedule temporarily.)

**Estimated cost** — check what a cycle will cost before running it:

```python
estimate = await agent.dreams.estimate_cost(depth="medium")
print(f"~${estimate.estimated_usd:.4f}  ({estimate.confidence} confidence)")
```

`estimate` is a `CostEstimate` with `estimated_usd`, `estimated_tokens`,
`confidence` (`"low"` / `"medium"` / `"high"` — based on how many prior
cycles of the same depth are in the ledger), `sample_size`, and
`window_days`.

---

## What Gets Skipped

Dream cycle phases interact with your `LockConfig`:

- **`memory_mode="append_only"` or `"read_only"`** — reconsolidation is
  skipped (can't merge or rewrite memories on a non-learning store)
- **`directive_evolution_mode="locked"`** — directive evolution is skipped
- **`freeze_decay=True`** — the decay/maintenance phase is skipped

If you've locked your agent for production, dream cycles still run journal
synthesis and goal extraction — the agent can still reflect, it just can't
modify its memories or directives.

---

## LLM Cost

Dream cycles make LLM calls. Rough estimates per cycle:

| Depth | Memories | Approximate cost |
|-------|----------|-----------------|
| Low | < 20 | $0.001 – $0.005 |
| Medium | 20–100 | $0.005 – $0.05 |
| High | 100+ | $0.05 – $0.50 |

Set a budget guard to prevent runaway spend:

```python
from wisdom_layer.config import ResourceLimits

config = AgentConfig(
    ...,
    resource_limits=ResourceLimits(monthly_budget_usd=5.0),
)
```

---

## Further Reading

- [Memory Architecture](memory-tiers.md) — what the cycle reads and writes
- [Directives](directives.md) — the behavioral rules the cycle evolves
- [API Reference](../api-reference.md) — `agent.dreams`, `DreamReport`
