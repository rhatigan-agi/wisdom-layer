"""Wisdom Layer SDK -- Quickstart (cloud LLM).

Free-tier example. Shows the basics:
  install -> capture -> semantic search -> status

Usage:
    pip install "wisdom-layer[anthropic]"
    ANTHROPIC_API_KEY=sk-ant-... python quickstart_cloud.py

For local / self-hosted models, see quickstart_local.py.
For the full cognitive loop (directives, critic, dream cycles), see
compounding_demo.py -- those features require a Pro license.
Get one at https://wisdomlayer.ai/pricing.

The agent's database persists at ~/.wisdom-layer/quickstart.db -- run this
script multiple times to see memories accumulate.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("quickstart")
logger.setLevel(logging.INFO)

DB_DIR = Path.home() / ".wisdom-layer"
DB_PATH = DB_DIR / "quickstart.db"


async def main() -> None:
    from wisdom_layer import AgentConfig, WisdomAgent
    from wisdom_layer.llm.anthropic import AnthropicAdapter
    from wisdom_layer.storage import SQLiteBackend

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.error("Set ANTHROPIC_API_KEY to run this demo")
        sys.exit(1)

    # --- 1. Wire up --------------------------------------------------------
    llm = AnthropicAdapter(api_key=api_key)
    DB_DIR.mkdir(parents=True, exist_ok=True)
    # bind_embedder() in agent.initialize() wires llm.embed into the
    # backend automatically — explicit embed_fn= is optional.
    backend = SQLiteBackend(str(DB_PATH))

    agent = WisdomAgent(
        agent_id="quickstart-agent",
        config=AgentConfig.for_dev(
            name="Support Agent",
            role="Customer support specialist",
        ),
        llm=llm,
        backend=backend,
    )
    await agent.initialize()
    logger.info("Agent '%s' ready (tier: %s)\n", agent.name, agent.tier.value)

    # --- 2. Capture memories -----------------------------------------------
    await agent.memory.capture(
        "conversation",
        {
            "user": "I'd like a refund for order #12345",
            "agent": "I can help with that. Let me look up your order.",
            "outcome": "refund_processed",
        },
    )
    await agent.memory.capture(
        "conversation",
        {
            "user": "Your product broke after two days!",
            "agent": "I'm sorry to hear that. Let me check our warranty policy.",
            "outcome": "warranty_replacement",
            "notes": "Customer frustrated -- needed empathy-first approach",
        },
        emotional_intensity=0.7,
    )
    await agent.memory.capture(
        "conversation",
        {
            "user": "Can I get a discount on my next order?",
            "agent": "I can offer 10% off as a loyalty reward.",
            "outcome": "discount_applied",
        },
    )
    logger.info("Captured 3 memories")

    # --- 3. Semantic search ------------------------------------------------
    results = await agent.memory.search("angry customer warranty", limit=3)
    logger.info("Search 'angry customer warranty' -> %d results", len(results))
    for r in results:
        logger.info("  [%.3f] %s", r["similarity"], r["content"].get("outcome", ""))

    # --- 4. Agent status ---------------------------------------------------
    logger.info("")
    display = await agent.status_display()
    logger.info(display)

    await agent.close()
    logger.info("\nDatabase saved at %s", DB_PATH)
    logger.info(
        "\nNext steps:\n"
        "  - Run this script again to see memories accumulate.\n"
        "  - For directives, the critic, and dream cycles (Pro tier),\n"
        "    see compounding_demo.py and critic_example.py.\n"
        "  - Get a Pro license at https://wisdomlayer.ai/pricing"
    )


if __name__ == "__main__":
    asyncio.run(main())
