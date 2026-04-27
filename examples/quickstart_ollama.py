"""Wisdom Layer SDK — Ollama quickstart.

Mirrors ``quickstart.py`` but runs against a local Ollama server. No API
key, no outbound network calls to third-party LLM providers.

Usage:
    # 1. Install + run Ollama (https://ollama.com)
    ollama serve &
    ollama pull llama3.2
    ollama pull nomic-embed-text

    # 2. Install the SDK with the Ollama extra
    pip install "wisdom-layer[ollama]"

    # 3. Run this script
    python quickstart_ollama.py

Override the server URL with ``OLLAMA_BASE_URL`` or pass
``base_url=...`` directly. Override the models with
``model=`` and ``embedding_model=``.

The agent database persists at ``~/.wisdom-layer/quickstart_ollama.db``.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from wisdom_layer import AgentConfig, WisdomAgent
from wisdom_layer.llm.ollama import OllamaAdapter
from wisdom_layer.storage import SQLiteBackend

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("quickstart_ollama")
logger.setLevel(logging.INFO)

DB_DIR = Path.home() / ".wisdom-layer"
DB_PATH = DB_DIR / "quickstart_ollama.db"


async def main() -> None:
    model = OllamaAdapter(
        model="llama3.2",
        embedding_model="nomic-embed-text",
    )

    if not await model.health_check():
        logger.error(
            "Ollama not reachable at %s — start it with `ollama serve`",
            model._base_url,
        )
        return

    DB_DIR.mkdir(parents=True, exist_ok=True)
    # bind_embedder() in agent.initialize() wires model.embed into the
    # backend automatically — explicit embed_fn= is optional.
    backend = SQLiteBackend(str(DB_PATH))

    agent = WisdomAgent(
        agent_id="quickstart-ollama",
        config=AgentConfig.for_dev(
            name="Local Support Agent",
            role="Customer support specialist",
        ),
        llm=model,
        backend=backend,
    )
    await agent.initialize()
    logger.info("Agent '%s' ready (tier: %s)\n", agent.name, agent.tier.value)

    await agent.memory.capture(
        "conversation",
        {
            "user": "I'd like a refund for order #12345",
            "agent": "I can help with that. Let me look up your order.",
            "outcome": "refund_processed",
        },
    )
    logger.info("Captured a memory")

    results = await agent.memory.search("refund", limit=3)
    logger.info("Semantic search → %d result(s)", len(results))

    await backend.close()
    await model.close()
    logger.info("Database saved at %s", DB_PATH)


if __name__ == "__main__":
    asyncio.run(main())
