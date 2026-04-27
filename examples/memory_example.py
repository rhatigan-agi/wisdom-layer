"""Wisdom Layer SDK -- Memory operations.

Demonstrates memory capture, search, sessions, export/import, and deletion.

Usage:
    pip install "wisdom-layer[anthropic]"
    ANTHROPIC_API_KEY=sk-ant-... python memory_example.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("memory_example")
logger.setLevel(logging.INFO)


async def main() -> None:
    from wisdom_layer import AgentConfig, WisdomAgent
    from wisdom_layer.llm.anthropic import AnthropicAdapter
    from wisdom_layer.storage import SQLiteBackend

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.error("Set ANTHROPIC_API_KEY to run this example")
        sys.exit(1)

    llm = AnthropicAdapter(api_key=api_key)
    agent = WisdomAgent(
        agent_id="memory-demo",
        config=AgentConfig.for_dev(name="Memory Demo Agent"),
        llm=llm,
        backend=SQLiteBackend(":memory:"),
    )
    await agent.initialize()

    # --- 1. Capture memories with different emotional intensities ----
    await agent.memory.capture(
        "incident",
        {"user": "Critical production outage affecting all customers", "severity": "p0"},
        emotional_intensity=0.9,
    )
    await agent.memory.capture(
        "support",
        {"user": "How do I configure webhook endpoints?", "outcome": "answered"},
        emotional_intensity=0.1,
    )
    await agent.memory.capture(
        "feedback",
        {"user": "Great job on the fast incident resolution!", "sentiment": "positive"},
        emotional_intensity=0.6,
    )
    logger.info("Captured 3 memories with varying emotional intensity")

    # --- 2. Semantic search -----------------------------------------
    results = await agent.memory.search("production issues", limit=3)
    logger.info("\nSearch 'production issues' -> %d results:", len(results))
    for r in results:
        logger.info("  [%.3f] %s", r["similarity"], str(r["content"])[:80])

    # --- 3. Session-scoped memory -----------------------------------
    async with agent.session(session_id="support-ticket-42") as session:
        await session.memory.capture(
            "context",
            {"note": "Customer is on the Enterprise plan with 50 agents"},
        )
        await session.memory.capture(
            "resolution",
            {"action": "Updated the webhook URL configuration"},
        )
        session_results = await session.memory.search("webhook", limit=3)
        logger.info("\nSession search -> %d results", len(session_results))

    # --- 4. Ephemeral session (nothing persists) --------------------
    async with agent.session(session_id="private", ephemeral=True) as session:
        await session.memory.capture("context", {"note": "Sensitive data discussed here"})
        logger.info("\nEphemeral session: memory captured but will not persist")

    # --- 5. Export memories -----------------------------------------
    bundle = await agent.memory.export()
    logger.info("\nExported %d memories", len(bundle.get("memories", [])))

    # --- 6. Delete a memory (GDPR Article 17) -----------------------
    if results:
        memory_id = results[0].get("id", results[0].get("memory_id", ""))
        if memory_id:
            report = await agent.memory.delete(memory_id)
            logger.info("\nDeleted memory: %d row(s) removed", report.deleted)

    await agent.close()
    logger.info("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
