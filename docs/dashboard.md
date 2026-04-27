# Dashboard

A read-and-write web UI for inspecting and operating a Wisdom Layer
agent: memories, directives, dream cycles, health, provenance.

The dashboard ships inside the main `wisdom-layer` package. There is
no separate dashboard distribution — install the `[dashboard]` extra
and the `wisdom-layer-dashboard` console script is on your `PATH`.

---

## Install

```bash
pip install "wisdom-layer[dashboard]"
```

For full functionality (chat, capture, dream cycles), also install an
LLM adapter:

```bash
pip install "wisdom-layer[dashboard,anthropic]"
```

Without an LLM adapter, the dashboard still runs — it falls back to a
placeholder LLM so you can browse stored data, but chat and dream
cycles will return placeholder responses.

---

## Quick Start

### 1. Set your environment

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export WISDOM_LAYER_LICENSE=wl_pro_...   # optional, see below
```

### 2. Launch

```bash
wisdom-layer-dashboard --db wisdom.db --agent-id my-agent
```

The dashboard listens on `http://127.0.0.1:8741` by default. Open it
in your browser.

> **Important.** The `--agent-id` value must match the `agent_id` you
> used when writing data with the SDK. A mismatch is the most common
> cause of "dashboard starts but shows no data."

---

## CLI Options

```
wisdom-layer-dashboard [OPTIONS]

Options:
  --host HOST         Bind host (default: 127.0.0.1)
  --port PORT         Bind port (default: 8741)
  --db PATH           SQLite database path (default: wisdom.db)
  --agent-id ID       Agent ID to load (default: dashboard-agent)
  --log-level LEVEL   DEBUG | INFO | WARNING | ERROR (default: INFO)
  --demo              Mount demo routes (seed, progress-day, reset)
```

The dashboard binds to `127.0.0.1` by default — it is not exposed on
your network. To expose it intentionally (e.g. inside a private VPC),
pass `--host 0.0.0.0` and put it behind your own auth proxy. The
dashboard does not ship with built-in authentication.

---

## Environment Variables

The dashboard CLI reads configuration from process environment only.
**It does not auto-load `.env` files.** This is deliberate — silent
`.env` autoloading causes hard-to-debug shell pollution issues across
projects (see [Setting your license key](quickstart.md#setting-your-license-key)
in the quickstart for the recommended pattern).

| Variable | Purpose |
|---|---|
| `WISDOM_LAYER_LICENSE` | Your license key (`wl_pro_...` / `wl_ent_...`). Omit for anonymous Free tier. |
| `ANTHROPIC_API_KEY` | Use Anthropic as the chat LLM. |
| `OPENAI_API_KEY` | Use OpenAI as the chat LLM. |
| `GOOGLE_API_KEY` / `GEMINI_API_KEY` | Use Gemini as the chat LLM. |
| `OLLAMA_HOST` | Use a local Ollama server. |
| `LITELLM_MODEL` + `LITELLM_EMBEDDING_MODEL` | Use LiteLLM (both required). |

LLM adapters are auto-detected in the order above — the first one
with a populated env var wins.

### Loading from a file

If you keep secrets in a `.env`, source it before launch:

```bash
set -a && source .env && set +a
wisdom-layer-dashboard --db wisdom.db --agent-id my-agent
```

Or load it in a wrapper script using `python-dotenv`:

```python
from dotenv import load_dotenv
load_dotenv()
import wisdom_layer.dashboard.cli as cli
cli.main()
```

---

## License Tiers in the Dashboard

The dashboard runs at whatever tier your license key resolves to:

- **No key** → anonymous Free tier. Browse memories and directives,
  view health snapshots. Pro features (dream cycles, critic, directive
  evolution) are gated.
- **`wl_pro_...`** → Pro tier. All Pro features enabled.
- **`wl_ent_...`** → Enterprise tier. All features enabled.

Get a key at [wisdomlayer.ai/pricing](https://wisdomlayer.ai/pricing).

---

## Troubleshooting

See [troubleshooting.md → "My dashboard won't connect"](troubleshooting.md#my-dashboard-wont-connect)
for common issues:

- `ModuleNotFoundError: No module named 'wisdom_layer.dashboard'`
- Dashboard starts but shows no data (agent-id mismatch)

---

## Programmatic Usage

You can also mount the dashboard inside your own FastAPI app:

```python
from wisdom_layer.dashboard.server import mount_dashboard

app = mount_dashboard(agent)  # agent: WisdomAgent already initialized
```

This is useful if you want to embed the dashboard alongside your own
routes, or front it with your own auth middleware.
