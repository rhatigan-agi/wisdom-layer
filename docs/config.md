# Configuration

The Wisdom Layer SDK ships with three layers of configuration: an
`AgentConfig` preset (what is this agent *for*?), an optional
`AdminDefaults` archetype (what kind of cognitive tuning suits its
domain?), and a `ResourceLimits` preset (what hardware is it running
on?). Most integrations stop after one decision.

---

## Decision tree

Start here:

1. **Pick an `AgentConfig` preset.**
   - `AgentConfig.for_dev()` -- local iteration. Verbose flags, short
     dream cadence, small memory footprint.
   - `AgentConfig.for_prod(name=...)` -- customer-facing. Daily dream
     schedule, full features, cloud-sized resources.
   - `AgentConfig.for_testing()` -- deterministic unit / integration
     tests. Dreams off, minimal resources.

2. **(Optional) Pick an archetype** when the default cognitive tuning
   does not fit your domain.
   - `AdminDefaults.balanced()` (default) -- general use.
   - `AdminDefaults.for_research()` -- long retention, creative synthesis.
   - `AdminDefaults.for_coding_assistant()` -- high-churn context, strict coherence.
   - `AdminDefaults.for_strategic_advisors()` -- institutional memory, high-stakes.
   - `AdminDefaults.for_lightweight_local()` -- small models, tight context budgets.
   - Compose with the preset:
     ```python
     AgentConfig.for_prod(name="researcher",
                          admin_defaults=AdminDefaults.for_research())
     ```

3. **(Optional) Pick a `ResourceLimits` preset** if the preset's
   defaults don't match your hardware.
   - `ResourceLimits.for_cloud()` -- generous, matches library defaults.
   - `ResourceLimits.for_local()` -- workstation / developer laptop running a local model.
   - `ResourceLimits.for_small_model()` -- 7B-class models, tight context, serial inference.

That's it for ~95% of integrations. Fine-grained tuning is still
available via the raw constructors for the rare case you need it.

---

## Minimal construction

```python
from wisdom_layer import WisdomAgent
from wisdom_layer.llm.anthropic import AnthropicAdapter

agent = WisdomAgent(
    name="demo",
    llm=AnthropicAdapter(api_key="sk-ant-..."),
)
```

Defaults used:
- `config` -> `AgentConfig.for_dev()` (or `for_prod()` if `ENV=production`).
- `agent_id` -> the `name` value.
- `storage` -> in-memory SQLite (logs a warning about non-persistence).

---

## Explicit construction

```python
from wisdom_layer import AgentConfig, WisdomAgent
from wisdom_layer.llm.anthropic import AnthropicAdapter
from wisdom_layer.storage import SQLiteBackend

model = AnthropicAdapter(api_key="sk-ant-...")
agent = WisdomAgent(
    agent_id="support-agent-001",
    config=AgentConfig.for_prod(
        name="Support Agent",
        role="Customer support specialist",
        # Pro features (directives, critic, dreams) require a paid key.
        # Get one at https://wisdomlayer.ai/pricing.
        api_key=os.environ["WISDOM_LAYER_LICENSE"],
    ),
    llm=model,
    # The backend's embedder is auto-wired from `model` at agent.initialize()
    # via bind_embedder — no embed_fn= needed.
    backend=SQLiteBackend("./agent.db"),
)
```

---

## Validation at init time

Construction runs validation synchronously -- errors surface at
`__init__`, not at first `await`:

| Check | Error |
|---|---|
| No LLM adapter passed | `ValueError` |
| Empty `agent_id=""` | `ValueError` |
| Dreams flagged on but LLM has no `generate` | `ConfigError` |

Tier/feature checks are enforced at call time by `_require_feature`,
so defaulted pro-tier flags on a free license are allowed at
construction and raise `TierRestrictionError` only if the feature is
actually invoked.

---

## When to use `template_mode`

For locked production agents where directives should not evolve and
memory is read-only:

```python
config = AgentConfig.template_mode(
    name="production-bot",
    role="Customer support specialist",
    directives=["Rule 1", "Rule 2"],
    # template_mode is a Pro feature — get a key at
    # https://wisdomlayer.ai/pricing.
    api_key=os.environ["WISDOM_LAYER_LICENSE"],
)
```

This sets `lock.directive_evolution_mode="locked"`,
`lock.memory_mode="read_only"`, `lock.freeze_decay=True`, and
`feature_flags.dreams=False` in one call.

---

## Feature flags

Toggle individual features on or off, independent of tier:

```python
from wisdom_layer import AgentConfig, FeatureFlags

config = AgentConfig.for_prod(
    name="My Agent",
    api_key=os.environ["WISDOM_LAYER_LICENSE"],
    feature_flags=FeatureFlags(
        dreams=False,
        critic=True,
        directives=True,
        health_analytics=True,
        cost_visibility=True,
        provenance=True,
        scheduled_dreams=True,
    ),
)
```

---

## Resource limits

```python
from wisdom_layer import ResourceLimits

limits = ResourceLimits(
    max_memories_per_agent=10_000,
    max_concurrent_llm_calls=2,
    dreams_phase_timeout_seconds=300,
    max_snapshot_seconds=30,
)

# Or use presets
limits = ResourceLimits.for_local()
limits = ResourceLimits.for_cloud()
limits = ResourceLimits.for_small_model()
```

---

## Retrieval mix

`AgentConfig.search_insight_ratio` (default `0.0`) reserves a fraction
of every `memory.search()` result slot for `reconsolidated_insight`
rows — distilled outputs from dream cycles. At the default `0.0`,
search is purely similarity-ordered (preserves legacy behavior). At
`0.4`, two of five slots in a `limit=5` search are reserved for
insights when any are available; the remaining three follow normal
similarity ranking.

```python
config = AgentConfig.for_prod(
    name="My Agent",
    api_key=os.environ["WISDOM_LAYER_LICENSE"],
    search_insight_ratio=0.4,  # surface dream insights alongside raw events
)
```

The reservation is automatically disabled when the caller passes an
explicit `kinds=` filter to `memory.search()` — that signal indicates
the caller is steering retrieval directly. Recommended range when
enabling: `0.20–0.40` for agents whose dream cycles have produced
high-signal insights worth surfacing proactively.

---

## Lock modes

```python
from wisdom_layer import LockConfig

lock = LockConfig(
    directive_evolution_mode="locked",
    memory_mode="read_only",
    freeze_decay=True,
)
```

Memory modes: `"learning"` (default), `"append_only"`, `"read_only"`.
Strictest-mode-wins when multiple config sources disagree.

For per-call ephemeral behaviour, use `agent.session(ephemeral=True)` —
that is a session parameter, not a `LockConfig` mode.
