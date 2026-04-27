"""Wisdom Layer SDK -- Quickstart for local / self-hosted models.

Free-tier example. Bring your own model server. This script works with
any inference backend that exposes an OpenAI-compatible API:

    - Ollama        -> http://localhost:11434/v1
    - vLLM          -> http://localhost:8000/v1
    - LM Studio     -> http://localhost:1234/v1
    - text-gen-webui -> http://localhost:5000/v1
    - LocalAI       -> http://localhost:8080/v1
    - Any OpenAI-compatible proxy

Configure the three constants below and run:

    pip install wisdom-layer
    python quickstart_local.py

The agent's database persists at ~/.wisdom-layer/quickstart.db -- run
this script multiple times to see memories accumulate.

For the full cognitive loop (directives, critic, dream cycles), see
compounding_demo.py -- those features require a Pro license.
Get one at https://wisdomlayer.ai/pricing.

---

What to change for your setup:

    BASE_URL    The base URL of your model server's OpenAI-compatible API.
                Most servers expose this at /v1. Ollama uses /v1 as well
                (requires Ollama 0.1.24+).

    CHAT_MODEL  The model name your server uses for chat completions.
                Examples: "qwen2.5:32b", "mistral-7b-instruct",
                "meta-llama/Llama-3-8b-instruct", "local-model"

    EMBED_MODEL The model name for embeddings. Some servers use the same
                model for both; others need a dedicated embedding model.
                Set to None to use sentence-transformers locally instead
                (requires: pip install sentence-transformers).
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

import httpx

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("quickstart")
logger.setLevel(logging.INFO)

BASE_URL = "http://localhost:11434/v1"
CHAT_MODEL = "qwen2.5:32b"
EMBED_MODEL = "qwen2.5:32b"

DB_DIR = Path.home() / ".wisdom-layer"
DB_PATH = DB_DIR / "quickstart.db"


async def chat_fn(
    messages: list[dict[str, str]],
    *,
    system: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Call an OpenAI-compatible /v1/chat/completions endpoint."""
    if system:
        messages = [{"role": "system", "content": system}, *messages]

    payload = {
        "model": CHAT_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{BASE_URL}/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()

    choice = data.get("choices", [{}])[0]
    usage = data.get("usage", {})
    return {
        "text": choice.get("message", {}).get("content", ""),
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "cost_usd": 0.0,
    }


async def embed_fn_remote(text: str) -> list[float]:
    """Call an OpenAI-compatible /v1/embeddings endpoint."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{BASE_URL}/embeddings",
            json={"model": EMBED_MODEL, "input": text},
        )
        resp.raise_for_status()
        data = resp.json()

    entries = data.get("data", [{}])
    return entries[0].get("embedding", []) if entries else []


def _get_local_embed_fn() -> Any:
    """Fall back to sentence-transformers for embeddings."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.error(
            "EMBED_MODEL is None and sentence-transformers is not installed.\n"
            "Either:\n"
            "  1. Set EMBED_MODEL to a model your server supports, or\n"
            "  2. pip install sentence-transformers",
        )
        sys.exit(1)

    st_model = SentenceTransformer("all-MiniLM-L6-v2")

    async def _embed(text: str) -> list[float]:
        vec = st_model.encode(text, normalize_embeddings=True)
        return vec.tolist()

    return _embed


async def main() -> None:
    from wisdom_layer import AgentConfig, WisdomAgent
    from wisdom_layer.llm.callable_adapter import CallableAdapter
    from wisdom_layer.storage import SQLiteBackend

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{BASE_URL}/models")
            resp.raise_for_status()
    except (httpx.ConnectError, httpx.ConnectTimeout):
        logger.error(
            "Cannot connect to model server at %s\n\n"
            "Make sure your model server is running. Common commands:\n"
            "  Ollama:    ollama serve\n"
            "  vLLM:      vllm serve %s\n"
            "  LM Studio: Start the app and enable the local server\n\n"
            "Then update BASE_URL at the top of this script if needed.",
            BASE_URL,
            CHAT_MODEL,
        )
        sys.exit(1)

    embed = embed_fn_remote if EMBED_MODEL else _get_local_embed_fn()

    llm = CallableAdapter(model_id=CHAT_MODEL, tier="high", fn=chat_fn)

    DB_DIR.mkdir(parents=True, exist_ok=True)
    backend = SQLiteBackend(str(DB_PATH), embed_fn=embed)

    agent = WisdomAgent(
        agent_id="quickstart-agent",
        config=AgentConfig.for_dev(
            name="Support Coach",
            role="Customer support specialist that learns from interactions",
        ),
        llm=llm,
        backend=backend,
    )
    await agent.initialize()
    logger.info("Agent '%s' ready (tier: %s)\n", agent.name, agent.tier.value)

    interactions = [
        {
            "event_type": "conversation",
            "data": {
                "user": "I'd like a refund for order #12345",
                "agent": "I can help with that. Let me look up your order.",
                "outcome": "refund_processed",
            },
        },
        {
            "event_type": "conversation",
            "data": {
                "user": "Your product broke after two days!",
                "agent": "I'm sorry to hear that. Let me check our warranty.",
                "outcome": "warranty_replacement",
                "notes": "Customer was frustrated -- empathy-first approach worked",
            },
            "emotional_intensity": 0.7,
        },
        {
            "event_type": "conversation",
            "data": {
                "user": "Can I get a discount on my next order?",
                "agent": "I can offer 10% off as a loyalty reward.",
                "outcome": "discount_applied",
            },
        },
    ]

    for interaction in interactions:
        await agent.memory.capture(
            interaction["event_type"],
            interaction["data"],
            emotional_intensity=interaction.get("emotional_intensity", 0.0),
        )
    logger.info("Captured %d memories", len(interactions))

    results = await agent.memory.search("angry customer warranty", limit=3)
    logger.info("Search 'angry customer warranty' -> %d results", len(results))
    for r in results:
        logger.info("  [%.3f] %s", r["similarity"], r["content"].get("outcome", ""))

    logger.info("")
    display = await agent.status_display()
    logger.info(display)

    await backend.close()
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
