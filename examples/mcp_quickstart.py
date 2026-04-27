"""Wisdom Layer SDK -- MCP Server Quickstart.

Sets up an agent and starts the Wisdom Layer MCP server, which exposes
the agent's memory, directives, health, and dream cycles to any
MCP-compatible AI tool (Claude Code, Cursor, Windsurf, etc.).

Usage:
    pip install "wisdom-layer[mcp,anthropic]"
    ANTHROPIC_API_KEY=sk-ant-... python mcp_quickstart.py

The server runs on stdio transport. To connect from Claude Code, add
this to .claude/settings.json:

    {
      "mcpServers": {
        "wisdom-layer": {
          "command": "wisdom-layer-mcp",
          "args": ["--db", "~/.wisdom-layer/mcp-demo.db", "--agent-id", "mcp-demo"],
          "env": { "ANTHROPIC_API_KEY": "sk-ant-..." }
        }
      }
    }

Or launch the server directly from the CLI:

    wisdom-layer-mcp --db ~/.wisdom-layer/mcp-demo.db --agent-id mcp-demo

See docs/mcp.md for the full list of available MCP tools.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("mcp_quickstart")
logger.setLevel(logging.INFO)

DB_DIR = Path.home() / ".wisdom-layer"
DB_PATH = DB_DIR / "mcp-demo.db"
AGENT_ID = "mcp-demo"


async def seed_agent() -> tuple[object, object]:
    """Seed the agent with a few memories. Returns (agent, backend)."""
    from wisdom_layer import AgentConfig, WisdomAgent
    from wisdom_layer.llm.anthropic import AnthropicAdapter
    from wisdom_layer.storage import SQLiteBackend

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.error("Set ANTHROPIC_API_KEY to run this demo")
        sys.exit(1)

    llm = AnthropicAdapter(api_key=api_key)
    DB_DIR.mkdir(parents=True, exist_ok=True)
    # bind_embedder() in agent.initialize() wires llm.embed into the
    # backend automatically — explicit embed_fn= is optional.
    backend = SQLiteBackend(str(DB_PATH))

    agent = WisdomAgent(
        agent_id=AGENT_ID,
        config=AgentConfig.for_dev(
            name="MCP Demo Agent",
            role="General-purpose assistant with persistent memory",
        ),
        llm=llm,
        backend=backend,
    )
    await agent.initialize()

    await agent.memory.capture(
        "observation",
        {"note": "User prefers concise responses with code examples over long explanations"},
    )
    await agent.memory.capture(
        "observation",
        {"note": "User is building a Python backend service with FastAPI and PostgreSQL"},
    )

    # Behavioral directives (`agent.directives.add(...)`) require a Pro
    # license. See examples/critic_example.py for a Pro-tier walkthrough,
    # or get a license at https://wisdomlayer.ai/pricing.

    health = await agent.health()
    logger.info(
        "Agent seeded: %d memories, wisdom_score=%.2f",
        health.memory_stats.consolidated_count + health.memory_stats.stream_count,
        health.wisdom_score or 0.0,
    )

    return agent, backend


async def main() -> None:
    from wisdom_layer.mcp.server import create_mcp_server

    agent, backend = await seed_agent()

    logger.info("\nStarting MCP server on stdio...")
    logger.info("Connect from Claude Code by adding this to .claude/settings.json:")
    logger.info(
        '  "wisdom-layer": { "command": "wisdom-layer-mcp",\n'
        '    "args": ["--db", "%s", "--agent-id", "%s"] }',
        DB_PATH,
        AGENT_ID,
    )
    logger.info("\nOr run the CLI directly:")
    logger.info("  wisdom-layer-mcp --db %s --agent-id %s\n", DB_PATH, AGENT_ID)

    mcp = create_mcp_server(agent)
    try:
        mcp.run(transport="stdio")
    finally:
        await backend.close()


if __name__ == "__main__":
    asyncio.run(main())
