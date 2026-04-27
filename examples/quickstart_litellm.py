"""Wisdom Layer SDK — LiteLLM quickstart.

Runs against any of the 100+ providers LiteLLM supports. This example
targets AWS Bedrock; swap the model string + env vars to point at
Azure, Cohere, Mistral, Together, OpenRouter, Ollama (local), vLLM, etc.

Usage:
    # 1. Install the SDK with the LiteLLM extra
    pip install "wisdom-layer[litellm]"

    # 2. Set the provider's credentials (LiteLLM env-var conventions)
    #    - Bedrock:  AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY /
    #                AWS_REGION_NAME
    #    - Azure:    AZURE_API_KEY / AZURE_API_BASE / AZURE_API_VERSION
    #    - Cohere:   COHERE_API_KEY
    #    - Together: TOGETHERAI_API_KEY
    #    - Ollama (local): no API key; just have ollama running
    #    - vLLM / OpenAI-compatible: OPENAI_API_KEY + api_base
    export AWS_REGION_NAME=us-east-1

    # 3. Run
    python quickstart_litellm.py

``embedding_model=`` is required.
    LiteLLMAdapter does not assume an embedding provider — pass the
    embedding model explicitly or construction raises ``ConfigError``.
    Pair the embedder with whatever your stack already uses:

| Chat model                                          | Embedding model                          |
|-----------------------------------------------------|------------------------------------------|
| ``bedrock/anthropic.claude-3-sonnet-...``           | ``bedrock/amazon.titan-embed-text-v2:0`` |
| ``azure/gpt-4``                                     | ``azure/text-embedding-3-small``         |
| ``ollama/llama3.1`` (local)                         | ``ollama/nomic-embed-text`` (local)      |
| ``openai/gpt-4o-mini``                              | ``openai/text-embedding-3-small``        |

    Prefer a *dedicated* embedding model. If you point ``embedding_model``
    at a chat model (e.g. ``ollama/qwen2.5-coder``) it will work — the
    adapter will pull a hidden-state vector — but similarity scores come
    back compressed (often 0.02–0.05 for clearly related content).
    Search ranking is still correct, but the absolute numbers will look
    "broken" to anyone reading them.

Model-string reference (a few of the top providers):

| Provider     | Example                                              |
|--------------|------------------------------------------------------|
| Bedrock      | ``bedrock/anthropic.claude-3-sonnet-20240229-v1:0``  |
| Azure OpenAI | ``azure/gpt-4``                                      |
| Cohere       | ``cohere/command-r``                                 |
| Mistral      | ``mistral/mistral-large-latest``                     |
| Together AI  | ``together_ai/meta-llama/Meta-Llama-3-70B-Instruct`` |
| OpenRouter   | ``openrouter/anthropic/claude-3.5-sonnet``           |
| Ollama       | ``ollama/llama3.1`` (chat) + ``ollama/nomic-embed-text`` (embed) |
| Perplexity   | ``perplexity/llama-3.1-sonar-large-128k-online``     |
| vLLM (local) | ``openai/<model-id>`` with ``api_base=...``          |
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from wisdom_layer import AgentConfig, WisdomAgent
from wisdom_layer.llm.litellm import LiteLLMAdapter
from wisdom_layer.storage import SQLiteBackend

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("quickstart_litellm")
logger.setLevel(logging.INFO)

DB_DIR = Path.home() / ".wisdom-layer"
DB_PATH = DB_DIR / "quickstart_litellm.db"


async def main() -> None:
    model = LiteLLMAdapter(
        model="bedrock/anthropic.claude-3-sonnet-20240229-v1:0",
        embedding_model="bedrock/amazon.titan-embed-text-v2:0",
        extra_params={"aws_region_name": "us-east-1"},
    )

    DB_DIR.mkdir(parents=True, exist_ok=True)
    # bind_embedder() in agent.initialize() wires model.embed into the
    # backend automatically — explicit embed_fn= is optional.
    backend = SQLiteBackend(str(DB_PATH))

    agent = WisdomAgent(
        agent_id="quickstart-litellm",
        config=AgentConfig.for_dev(
            name="LiteLLM-routed Agent",
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


if __name__ == "__main__":
    asyncio.run(main())
