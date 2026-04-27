# MCP Server Integration

Expose your Wisdom Layer agent's capabilities to any MCP-compatible
AI tool -- Claude Code, Cursor, Windsurf, and more.

The MCP server gives AI assistants direct access to your agent's
memory, directives, health monitoring, dream cycles, and provenance
tracking through the standard Model Context Protocol.

---

## Install

```bash
pip install "wisdom-layer[mcp]"
```

With an LLM adapter for full functionality:
```bash
pip install "wisdom-layer[mcp,anthropic]"
export ANTHROPIC_API_KEY=sk-ant-...
```

---

## Quick Start

### 1. Start the MCP server

```bash
wisdom-layer-mcp --db wisdom.db --agent-id my-agent
```

The server starts on stdio transport by default (required for
Claude Code and Cursor integration).

### 2. Configure Claude Code

Add to your `.claude/settings.json` or project-level
`.claude/settings.local.json`:

```json
{
  "mcpServers": {
    "wisdom-layer": {
      "command": "wisdom-layer-mcp",
      "args": ["--db", "/path/to/wisdom.db", "--agent-id", "my-agent"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

### 3. Configure Cursor

Add to your `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "wisdom-layer": {
      "command": "wisdom-layer-mcp",
      "args": ["--db", "/path/to/wisdom.db", "--agent-id", "my-agent"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

---

## Available Tools

| Tool | Description |
|------|-------------|
| `wisdom_capture` | Store a memory (observation, interaction, feedback) |
| `wisdom_recall` | Semantic search across all memory tiers |
| `wisdom_health` | Get the agent's cognitive health report |
| `wisdom_directives` | List active behavioral directives |
| `wisdom_add_directive` | Add a new behavioral rule |
| `wisdom_dream` | Trigger a reflection cycle |
| `wisdom_provenance` | Trace the origin/history of any entity |

### Example Tool Calls

**Capture a memory:**
```
wisdom_capture(event_type="observation", content="User prefers Python over JavaScript")
```

**Search memories:**
```
wisdom_recall(query="user preferences programming languages", limit=5)
```

**Check health:**
```
wisdom_health()
-> {"wisdom_score": 0.72, "classification": "healthy", ...}
```

**Trigger reflection:**
```
wisdom_dream()
-> {"cycle_id": "abc123", "steps": [...], "status": "completed"}
```

---

## Available Resources

Resources are read-only data the AI tool can load into context:

| Resource URI | Description |
|--------------|-------------|
| `wisdom://config` | Agent configuration (name, role, tier) |
| `wisdom://directives` | Active directives as structured data |
| `wisdom://health` | Current health report snapshot |

---

## CLI Options

```
wisdom-layer-mcp [OPTIONS]

Options:
  --db PATH           SQLite database path (default: wisdom.db)
  --agent-id ID       Agent ID to use (default: mcp-agent)
  --transport TYPE    stdio | sse | streamable-http (default: stdio)
  --log-level LEVEL   DEBUG | INFO | WARNING | ERROR (default: WARNING)
```

**Note:** For stdio transport, logs go to stderr (not stdout) to
avoid corrupting the MCP protocol stream.

---

## Programmatic Usage

You can also create the MCP server in your own code:

```python
import asyncio
from wisdom_layer.agent import WisdomAgent
from wisdom_layer.mcp.server import create_mcp_server

agent = WisdomAgent(...)
await agent.initialize()

mcp = create_mcp_server(agent)
mcp.run(transport="stdio")
```

---

## LLM Adapter Auto-Detection

The CLI automatically detects which LLM adapter to use based on
environment variables, checked in order:

1. `ANTHROPIC_API_KEY` -> Anthropic (Claude)
2. `OPENAI_API_KEY` -> OpenAI (GPT)
3. None -> FakeLLM (browsing stored data only; dream/capture won't work)

---

## What Can You Do With This?

Once configured, your AI assistant can:

- **Remember context** across conversations via `wisdom_capture`
- **Recall relevant information** from past sessions via `wisdom_recall`
- **Monitor agent health** and get improvement suggestions
- **Add behavioral rules** that persist and evolve over time
- **Trigger reflection** to consolidate learning
- **Trace provenance** of any memory, directive, or journal entry

The agent learns and improves autonomously -- the MCP interface
just makes its capabilities accessible to other AI tools.
