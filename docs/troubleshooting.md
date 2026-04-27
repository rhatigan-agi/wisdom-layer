# Troubleshooting

If you hit an error and the stack trace isn't enough, search this file by
symptom. Entries are organized by what you *see*, not by error class.

If your issue isn't covered here, open an issue at
<https://github.com/rhatigan-agi/wisdom-layer/issues>.

---

## "I just installed it and nothing imports"

### `ImportError: cannot import name 'AnthropicAdapter'` (or `OpenAIAdapter`, `GeminiAdapter`, `LiteLLMAdapter`)

**Likely cause.** You installed the base `wisdom-layer` wheel but not the
provider extra. Paid-provider adapters are optional extras so that
free-tier users don't have to pull down SDKs they don't use.

**Fix.**

```bash
pip install 'wisdom-layer[anthropic]'   # Claude
pip install 'wisdom-layer[openai]'      # GPT-4, GPT-4o
pip install 'wisdom-layer[gemini]'      # Gemini
pip install 'wisdom-layer[litellm]'     # LiteLLM router (any provider)
pip install 'wisdom-layer[all-adapters]'  # everything above
```

Ollama needs no extra (`httpx` is already a core dep).

### `ModelAdapterError: sentence-transformers required for embeddings`

**Likely cause.** The paid-provider adapters use `sentence-transformers`
for local embedding (they don't bill you for embedding calls). The package
isn't pulled in automatically.

**Fix.**

```bash
pip install sentence-transformers
```

First use will download the embedding model (~90 MB). Subsequent runs hit
the local HuggingFace cache.

### Wheel imports fine but Python complains about the version

The SDK requires Python 3.11+. If you're on 3.10 or older, `pip install`
succeeds but imports fail later on syntax. Upgrade Python or use a 3.11+
venv.

---

## "My first capture hangs or fails"

### It hangs on the first call only

**Likely cause.** The embedding model is downloading for the first time.
The default is `all-MiniLM-L6-v2` (~90 MB).

**Where the cost lands.** As of v1.0, the Anthropic, OpenAI, and Gemini
adapters eagerly load (and prime) the embedder during
`await agent.initialize()` rather than on the first `memory.capture` /
`memory.search`. The download / cold-start cost is the same — it just
happens at the spot you expect to be slow (boot) instead of mid-request.

**Diagnosis.** Raise logging to INFO — `initialize()` emits
`"Embedding model loaded"` once the download completes.

**Fix.** Wait it out once; the model is cached under
`~/.cache/huggingface/`. Pre-download on CI to avoid the first-boot
penalty:

```python
from sentence_transformers import SentenceTransformer
SentenceTransformer('all-MiniLM-L6-v2')
```

### `WARNING Embedder warmup skipped: sentence-transformers not installed`

**Likely cause.** You constructed an Anthropic / OpenAI / Gemini
adapter without the embedding extra. `agent.initialize()` tries to warm
the local embedder so first-search is fast, sees the missing dep, logs a
warning, and continues.

**When it's safe to ignore.** If you only use directives, the critic, or
journals — anything that doesn't need `memory.search` or `memory.capture`
— this is harmless. The warning is informational, not an error.

**Fix (if you do use memory).** Install the embedding dep that ships
with each cloud extra:

```bash
pip install "wisdom-layer[anthropic]"   # or [openai], [gemini]
```

The first real `memory.capture` will otherwise raise
`ModelAdapterError: sentence-transformers required for embeddings`.

### `ModelAdapterError: Ollama is not reachable at http://localhost:11434/...`

**Likely cause.** Ollama server isn't running, isn't on the default
port, or is blocked by a firewall.

**Fix.**

```bash
ollama serve    # in a separate terminal
```

Or point the adapter at a remote instance:

```python
OllamaAdapter(base_url="http://my-ollama-host:11434")
```

Or set `OLLAMA_BASE_URL` in your environment — the adapter picks it up
when you don't pass `base_url=` explicitly.

### `ModelAdapterError: Ollama model 'llama3.2' not found`

**Fix.** Pull the model first:

```bash
ollama pull llama3.2
ollama pull nomic-embed-text    # if you use Ollama for embeddings
```

### `BackendNotInitializedError: Backend not initialized. Call initialize() first.`

You forgot `await agent.initialize()`. Every capture/dream/search call
requires the backend to have run its migrations.

```python
agent = WisdomAgent(name="demo", llm=...)
await agent.initialize()        # required
await agent.memory.capture(...)
```

The sync wrapper has the same requirement:

```python
with SyncWisdomAgent(name="demo", llm=...) as agent:
    agent.initialize()          # required
    agent.memory.capture(...)
```

**Backward compat.** `BackendNotInitializedError` inherits from both
`StorageError` and `RuntimeError`, so existing code that does
`except RuntimeError` keeps working. New code should catch the typed
exception:

```python
from wisdom_layer.errors import BackendNotInitializedError

try:
    await agent.memory.search("hello")
except BackendNotInitializedError:
    ...
```

---

## "My dream cycle errors out"

### `FeatureDisabledError: 'dreams' is disabled via feature_flags.dreams`

**Likely cause.** You used `AgentConfig.for_testing(...)` — the testing
preset hardcodes `FeatureFlags(dreams=False)` so unit tests don't
accidentally incur LLM cost. Production presets (`production()`,
`local_dev()`) leave dreams on by default.

**Fix.** Override the flag explicitly:

```python
config = AgentConfig.for_testing(
    name="x",
    api_key=os.environ["WISDOM_LAYER_LICENSE"],
).model_copy(update={"feature_flags": FeatureFlags()})
```

### `TierRestrictionError: 'dreams' requires the pro tier`

**Likely cause.** You're on the free tier. Dream cycles are a paid
feature.

**Fix.** Set `api_key=os.environ["WISDOM_LAYER_LICENSE"]` on your
`AgentConfig` and export a Pro key (get one at
[wisdomlayer.ai/pricing](https://wisdomlayer.ai/pricing)). The free
tier still captures memories — it just doesn't run reconsolidation.

### The cycle runs but the result says `"status": "skipped"`

**Likely cause.** Not enough candidate memories — reconsolidation needs
a minimum number of nearby embeddings to form a cluster. A brand-new
agent will skip until it has captured enough.

**Diagnosis.** Check the `"reason"` field in the returned dict. Common
values: `"insufficient_candidates"`, `"budget_exhausted"`.

**Fix.** Capture more memories, or lower the threshold with
`DreamConfig(min_cluster_size=...)` if you know what you're doing.

### `LLMFailureError: All models in tier 'high' failed`

**Likely cause.** Rate limit, timeout, or a provider outage. The router
tried every adapter registered at the requested tier and they all
errored out.

**Fix.** Check `last_error` on the exception. If it's a rate limit,
retry with backoff. If it's auth, check `ANTHROPIC_API_KEY` /
`OPENAI_API_KEY` are set correctly.

---

## "My license key says invalid"

### `LicenseInvalidError` on agent initialize

**Likely cause.** Wrong format. Wisdom Layer keys look like
`wl_<tier>_<suffix>`, e.g. `wl_pro_abc123`. Anthropic-style `sk-ant-...`
keys are for the Anthropic LLM adapter — they are not Wisdom Layer
license keys.

**Fix.** Sign up at <https://wisdomlayer.ai/signup> for a free key, or
check your dashboard for the key you were issued.

### `LicenseExpiredError`

**Likely cause.** Your subscription lapsed. The SDK gives you an offline
grace period (default 7 days) before it hard-fails.

**Fix.** Renew your subscription, then restart your process so the SDK
re-fetches the license.

### Offline grace period warning

The SDK caches your license status. If the licensing API is unreachable,
you'll see a warning and the cached tier stays in effect for
`license_grace_days` (default 7). After that, the SDK drops to free.

---

## "My agent's behavior drifted unexpectedly"

### Directives appear or disappear unexpectedly

Dream cycles can legitimately propose new directives or decay old ones.
Check `agent.journals.latest()` for the cycle's summary.

If you want directives frozen, set
`LockConfig(directive_evolution_mode="locked")`. Attempts to mutate
directives then raise `DirectiveLockedError`.

### Archetype / personality mismatch across restarts

Archetype is stored in `AgentConfig.personality`, not in the database.
If you construct the agent with a different `PersonalityConfig` on
restart, you'll see behavior drift even though memories are intact.

### Suspected ephemeral-session leak

`async with agent.session(..., ephemeral=True)` should leave zero trace
in persistent storage — captures during the session never touch the DB,
and the next dream cycle cannot see them.

If you suspect a leak, open an issue at
<https://github.com/rhatigan-agi/wisdom-layer/issues> with a minimal
reproducer. Include the SDK version, backend type, and any custom
`MemoryMode` or `LockConfig` settings.

---

## "My database won't open"

### `StorageMigrationError` on initialize

**Likely cause.** A migration file is malformed. This should not happen
on a released SDK version.

**Fix.** File a bug at <https://github.com/rhatigan-agi/wisdom-layer/issues>
with the full stack trace and your SDK version.

### `StorageBusyError` / `sqlite3.OperationalError: database is locked`

**Likely cause.** Another process has the SQLite file open — a second
agent instance, a `sqlite3` CLI session, or a DB browser. SQLite's WAL
mode allows many readers but only one writer.

**Fix.** Close the other process. If you need real concurrent writers,
use the Postgres backend:

```bash
pip install "wisdom-layer[postgres]"
```

### `sqlite3.OperationalError: unable to open database file`

**Likely cause.** The parent directory doesn't exist, or you don't have
write permission.

**Fix.** Create the parent directory and verify permissions:

```bash
mkdir -p /path/to/data
ls -ld /path/to/data
```

### `EmbeddingDimensionMismatchError` on first search

**Likely cause.** You seeded memories with one embedding model and later
swapped to another with a different vector dimension.

**Fix.** Revert to the original embedder, or re-embed existing memories
with the new one by exporting and re-capturing. Automated re-embedding is
on the roadmap for a future release.

### `EmbeddingConfigMismatchError` at `agent.initialize()`

**Likely cause.** You set `embedding_model_id=` or `embedding_dim=`
explicitly on the storage backend AND those values disagree with what
the LLM adapter advertises. The agent's `bind_embedder` step refuses
to start with a backend pointed at one model and an adapter producing
vectors for another — that combination silently corrupts vector search.

**Fix.** Drop the explicit `embedding_model_id=` / `embedding_dim=` from
the backend constructor and let `bind_embedder` thread the adapter's
values through automatically:

```python
# Before (forces you to keep three knobs in sync)
llm = AnthropicAdapter(api_key=..., embedding_model="all-MiniLM-L6-v2")
backend = SQLiteBackend(
    "agent.db",
    embed_fn=llm.embed,
    embedding_model_id="all-MiniLM-L6-v2",  # remove this
    embedding_dim=384,                        # remove this
)

# After (single source of truth on the adapter)
llm = AnthropicAdapter(api_key=..., embedding_model="all-MiniLM-L6-v2")
backend = SQLiteBackend("agent.db")
```

If you genuinely need two different models (e.g. legacy data tagged
under a different identifier), keep the explicit override and update
the adapter to match.

### `EmbeddingConfigMismatchError: PostgresBackend hard-codes VECTOR(384)`

**Likely cause.** Your LLM adapter advertises a non-384 embedding dim
(e.g. `text-embedding-3-small` is 1536). Postgres v0.6 fixes vector
columns at 384 in its initial migration.

**Fix.** Swap the adapter's `embedding_model=` to a 384-dim model
(e.g. `all-MiniLM-L6-v2`), or use `SQLiteBackend` until parameterized
Postgres dim ships.

---

## "My dashboard won't connect"

### `ModuleNotFoundError: No module named 'wisdom_layer.dashboard'`

**Likely cause.** Dashboard is an optional extra.

**Fix.**

```bash
pip install "wisdom-layer[dashboard]"
```

### Dashboard starts but shows no data

**Likely cause.** The agent ID in the dashboard doesn't match the one
used to write data.

**Diagnosis.** Verify `--agent-id` matches the `agent_id` used in your
SDK code.

---

## "Postgres backend won't connect"

### `asyncpg.InvalidCatalogNameError` or connection refused

**Likely cause.** DSN is wrong, Postgres isn't running, or the database
doesn't exist.

**Fix.** Verify your DSN and create the database:

```bash
createdb wisdom
```

```python
backend = PostgresBackend(
    dsn="postgresql://user:pass@localhost:5432/wisdom",
)  # embedder auto-wired from llm at agent.initialize()
```

### `pgvector extension not found`

**Likely cause.** The `vector` extension isn't installed in Postgres.

**Fix.**

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

On managed Postgres (RDS, Supabase), enable it via the extensions panel.

---

## "LangGraph integration import fails"

### `ImportError: cannot import name 'WisdomRecallNode'`

**Likely cause.** Missing the integration extra.

**Fix.**

```bash
pip install "wisdom-layer[langgraph]"
```

---

## "MCP server won't start"

### `ModuleNotFoundError: No module named 'mcp'`

**Likely cause.** Missing the MCP extra.

**Fix.**

```bash
pip install "wisdom-layer[mcp]"
```

### MCP server starts but no LLM tools work

**Likely cause.** No LLM API key found. The CLI auto-detects your LLM
from environment variables: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`,
`GOOGLE_API_KEY`, `OLLAMA_HOST`, `LITELLM_MODEL` (checked in that order).
Without any, it runs in browse-only mode.

**Fix.** Set the appropriate API key in your environment.

---

## "Budget or cost errors"

### `BudgetExceededError` on dream trigger

**Likely cause.** Your daily or monthly spend cap has been reached.
`BudgetGuard` enforces limits and puts the agent on cooldown.

**Diagnosis.** Check `await agent.cost.summary()` for current spend.

**Fix.** Wait for the cooldown to expire, or raise the budget in
`ResourceLimits`.

---

## Still stuck?

Open an issue at <https://github.com/rhatigan-agi/wisdom-layer/issues>.
Include your SDK version (`import wisdom_layer; print(wisdom_layer.__version__)`),
the full exception and stack trace, and the minimal code that reproduces it.
