"""Wisdom Layer SDK — Compounding Demo.

Proves that the agent gets better over multiple runs. Each execution:
  1. Loads the persistent agent (or creates it on first run)
  2. Shows what's changed since last run
  3. Captures new interactions (different each run)
  4. Triggers a dream cycle
  5. Shows the evolution diff

Run this script 3+ times to see the agent accumulate knowledge,
consolidate memories into insights, and evolve behavioral directives.

This example demonstrates Pro-tier features (directive evolution,
dream cycles, critic). It requires a Pro license. Get one at
https://wisdomlayer.ai/pricing.

For Free-tier examples that work without a license, see:
  - basic_agent.py
  - memory_example.py
  - quickstart_cloud.py
  - quickstart_local.py
  - mcp_quickstart.py
  - langgraph_quickstart.py

Usage:
    pip install wisdom-layer
    WISDOM_LAYER_LICENSE=wl_pro_... python compounding_demo.py          # Uses local model server
    WISDOM_LAYER_LICENSE=wl_pro_... python compounding_demo.py --cloud  # Uses Anthropic API

For local mode, configure BASE_URL and MODEL below for your server
(Ollama, vLLM, LM Studio, etc.). See quickstart_local.py for details.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

import httpx

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("compounding")
logger.setLevel(logging.INFO)

DB_DIR = Path.home() / ".wisdom-layer"
DB_PATH = DB_DIR / "compounding.db"

# ┌──────────────────────────────────────────────────────────────────┐
# │  CONFIGURE FOR YOUR LOCAL MODEL SERVER                          │
# └──────────────────────────────────────────────────────────────────┘
BASE_URL = "http://localhost:11434/v1"  # Ollama default
CHAT_MODEL = "qwen2.5:32b"
EMBED_MODEL = "qwen2.5:32b"            # Set to None for local embeddings
# ──────────────────────────────────────────────────────────────────

# --- Interaction sets (one per run, cycling) ---------------------------------

INTERACTION_SETS: list[list[dict[str, Any]]] = [
    # Run 1: Basic customer support scenarios
    [
        {
            "type": "conversation",
            "data": {
                "user": "I want a refund but I lost my receipt",
                "agent": "I can look up your purchase by email address.",
                "outcome": "refund_processed",
                "lesson": "Always offer alternative lookup methods",
            },
        },
        {
            "type": "conversation",
            "data": {
                "user": "Why is your shipping so slow?",
                "agent": "I apologize for the delay. Let me check your order status.",
                "outcome": "shipping_expedited",
                "lesson": "Acknowledge frustration before problem-solving",
            },
            "emotional_intensity": 0.6,
        },
        {
            "type": "conversation",
            "data": {
                "user": "I love your product! How do I get more?",
                "agent": "Thank you! I can set you up with a subscription.",
                "outcome": "upsell_subscription",
                "lesson": "Positive interactions are upsell opportunities",
            },
        },
    ],
    # Run 2: Escalation patterns
    [
        {
            "type": "conversation",
            "data": {
                "user": "I've called three times about this issue!",
                "agent": "I'm sorry you've had to reach out multiple times. "
                "Let me review your case history and resolve this now.",
                "outcome": "escalation_resolved",
                "lesson": "Repeat contacts need immediate ownership",
            },
            "emotional_intensity": 0.8,
        },
        {
            "type": "conversation",
            "data": {
                "user": "Your competitor offers free returns",
                "agent": "I understand the concern. Let me see what we can do "
                "to make our return process easier for you.",
                "outcome": "retention_save",
                "lesson": "Never argue with competitor comparisons",
            },
        },
        {
            "type": "observation",
            "data": {
                "pattern": "Customers who mention competitors are 3x more "
                "likely to churn within 30 days",
                "source": "quarterly_analysis",
            },
        },
    ],
    # Run 3: Complex scenarios
    [
        {
            "type": "conversation",
            "data": {
                "user": "I was charged twice for the same order",
                "agent": "I see the duplicate charge. I'm issuing a refund "
                "right now and adding a credit for the inconvenience.",
                "outcome": "billing_error_fixed",
                "lesson": "Proactive credit builds trust after errors",
            },
            "emotional_intensity": 0.5,
        },
        {
            "type": "conversation",
            "data": {
                "user": "Can you help me set up the product? The manual is confusing.",
                "agent": "Of course! Let me walk you through it step by step.",
                "outcome": "setup_completed",
                "lesson": "Product complexity drives support volume",
            },
        },
        {
            "type": "observation",
            "data": {
                "pattern": "Customers who get setup help in first week have "
                "40% higher retention",
                "source": "onboarding_metrics",
            },
        },
        {
            "type": "conversation",
            "data": {
                "user": "I want to cancel my subscription",
                "agent": "I'm sorry to hear that. Before I process the "
                "cancellation, may I ask what prompted this decision?",
                "outcome": "retention_attempted",
                "lesson": "Always understand churn reason before processing",
            },
            "emotional_intensity": 0.4,
        },
    ],
]


# --- OpenAI-compatible model server helpers ----------------------------------


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
        resp = await client.post(
            f"{BASE_URL}/chat/completions", json=payload,
        )
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


async def embed_fn(text: str) -> list[float]:
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


# --- Main --------------------------------------------------------------------


async def main() -> None:
    import os

    from wisdom_layer import AgentConfig, WisdomAgent
    from wisdom_layer.storage import SQLiteBackend

    wisdom_layer_license = os.environ.get("WISDOM_LAYER_LICENSE")
    if not wisdom_layer_license:
        logger.error(
            "This example requires a Pro license.\n"
            "Get one at https://wisdomlayer.ai/pricing\n\n"
            "Then re-run with:\n"
            "    WISDOM_LAYER_LICENSE=wl_pro_... python compounding_demo.py\n\n"
            "For Free-tier examples, see basic_agent.py, memory_example.py,\n"
            "quickstart_cloud.py, quickstart_local.py, mcp_quickstart.py,\n"
            "or langgraph_quickstart.py.",
        )
        sys.exit(1)

    use_cloud = "--cloud" in sys.argv

    if use_cloud:
        from wisdom_layer.llm.anthropic import AnthropicAdapter

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            logger.error("Set ANTHROPIC_API_KEY for --cloud mode")
            sys.exit(1)
        model_adapter = AnthropicAdapter(api_key=api_key)
        chosen_embed_fn = model_adapter.embed
    else:
        from wisdom_layer.llm import CallableAdapter

        # Verify model server is reachable
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{BASE_URL}/models")
                resp.raise_for_status()
        except (httpx.ConnectError, httpx.ConnectTimeout):
            logger.error(
                "Cannot connect to model server at %s\n\n"
                "Make sure your server is running, then update BASE_URL\n"
                "at the top of this script. Or use --cloud for Anthropic API.",
                BASE_URL,
            )
            sys.exit(1)

        model_adapter = CallableAdapter(
            model_id=CHAT_MODEL,
            tier="high",
            fn=chat_fn,
        )
        chosen_embed_fn = embed_fn

    # --- Setup ---------------------------------------------------------------
    DB_DIR.mkdir(parents=True, exist_ok=True)
    backend = SQLiteBackend(str(DB_PATH), embed_fn=chosen_embed_fn)

    agent = WisdomAgent(
        agent_id="compounding-agent",
        config=AgentConfig(
            name="Support Coach",
            role="Customer support specialist that learns from interactions",
            api_key=wisdom_layer_license,
        ),
        model=model_adapter,
        backend=backend,
    )
    await agent.initialize()

    # --- Snapshot before ------------------------------------------------------
    status_before = await agent.status()
    evo_before = status_before.get("evolution_summary", {})
    counts_before = status_before.get("counts", {})
    mem_before = counts_before.get("memories", 0)
    dir_before = evo_before.get("directives_by_status", {})
    dream_before = evo_before.get("dream_count", 0)

    # Determine run number from dream count
    run_number = dream_before + 1

    logger.info("=" * 60)
    logger.info("=== Run #%d ===", run_number)
    logger.info("=" * 60)

    if run_number == 1:
        logger.info("\nFirst run — agent starts from scratch.\n")
    else:
        logger.info("\nAgent state from previous runs:")
        display = await agent.status_display()
        logger.info(display)
        logger.info("")

    # --- Capture new interactions --------------------------------------------
    set_index = (run_number - 1) % len(INTERACTION_SETS)
    interactions = INTERACTION_SETS[set_index]

    logger.info("Capturing %d new interactions...", len(interactions))
    for interaction in interactions:
        await agent.memory.capture(
            interaction["type"],
            interaction["data"],
            emotional_intensity=interaction.get("emotional_intensity", 0.0),
        )

    # --- Search quality demo -------------------------------------------------
    results = await agent.memory.search(
        "frustrated customer wants to leave", limit=3,
    )
    logger.info(
        "\nSearch 'frustrated customer wants to leave' → %d results",
        len(results),
    )
    for r in results:
        content = r["content"]
        preview = content.get("lesson") or content.get("pattern") or str(content)[:60]
        logger.info("  [%.3f] %s", r["similarity"], preview)

    # --- Dream cycle ---------------------------------------------------------
    logger.info("\nTriggering dream cycle...")
    report = await agent.dreams.trigger()
    logger.info("Dream cycle complete:")
    logger.info(report["summary"])

    # --- Snapshot after -------------------------------------------------------
    status_after = await agent.status()
    evo_after = status_after.get("evolution_summary", {})
    counts_after = status_after.get("counts", {})
    mem_after = counts_after.get("memories", 0)
    dir_after = evo_after.get("directives_by_status", {})
    dream_after = evo_after.get("dream_count", 0)

    # --- Diff -----------------------------------------------------------------
    mem_delta = mem_after - mem_before
    dir_active_before = (
        dir_before.get("active", 0) + dir_before.get("provisional", 0)
        + dir_before.get("permanent", 0)
    )
    dir_active_after = (
        dir_after.get("active", 0) + dir_after.get("provisional", 0)
        + dir_after.get("permanent", 0)
    )
    dir_delta = dir_active_after - dir_active_before
    dream_delta = dream_after - dream_before

    logger.info("\n--- What changed this run ---")
    logger.info("  +%d new memories captured", mem_delta)
    if dir_delta > 0:
        logger.info("  +%d directive(s) added or promoted", dir_delta)
    if dream_delta > 0:
        logger.info("  +%d dream cycle(s) completed", dream_delta)

    consolidated = evo_after.get("total_consolidated", 0)
    if consolidated:
        logger.info(
            "  %d total memories consolidated into higher-order insights",
            consolidated,
        )

    # --- Final status ---------------------------------------------------------
    logger.info("\n--- Agent status after run #%d ---", run_number)
    display = await agent.status_display()
    logger.info(display)

    await agent.close()

    logger.info("\nDatabase at %s", DB_PATH)
    if run_number < 3:
        logger.info(
            "Run this script again to see the agent evolve further! "
            "(Run %d of 3+ recommended)",
            run_number + 1,
        )
    else:
        logger.info(
            "The agent now has %d runs of accumulated experience. "
            "Each run makes it better.",
            run_number,
        )


if __name__ == "__main__":
    asyncio.run(main())
