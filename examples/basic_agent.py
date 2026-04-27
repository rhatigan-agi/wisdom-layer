"""Wisdom Layer SDK -- Minimal agent setup.

The simplest possible Wisdom Layer agent: create, capture, search, shutdown.
No dream cycles, no directives -- just persistent memory.

Usage:
    pip install "wisdom-layer[anthropic]"
    ANTHROPIC_API_KEY=sk-ant-... python basic_agent.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from wisdom_layer import AgentConfig, WisdomAgent
from wisdom_layer.llm.anthropic import AnthropicAdapter
from wisdom_layer.storage import SQLiteBackend

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("basic_agent")
logger.setLevel(logging.INFO)


async def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.error("Set ANTHROPIC_API_KEY to run this example")
        sys.exit(1)
    llm = AnthropicAdapter(api_key=api_key)

    agent = WisdomAgent(
        agent_id="basic-agent",
        config=AgentConfig.for_dev(name="Basic Agent"),
        llm=llm,
        backend=SQLiteBackend(":memory:"),
    )
    await agent.initialize()
    logger.info("Agent ready (tier: %s)", agent.tier.value)

    await agent.memory.capture(
        "observation",
        {"note": "User prefers concise answers over detailed explanations"},
    )
    await agent.memory.capture(
        "conversation",
        {"user": "Asked about pricing", "outcome": "satisfied with Pro tier"},
    )
    logger.info("Captured 2 memories")

    results = await agent.memory.search("pricing", limit=3)
    logger.info("Search 'pricing' -> %d result(s)", len(results))
    for r in results:
        logger.info("  [%.3f] %s", r["similarity"], r["content"])

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
