"""Wisdom Layer SDK -- Critic and directives.

Demonstrates adding directives, evaluating output against them,
and using the critic to flag risky responses.

This example demonstrates Pro-tier features (directive evolution,
critic). It requires a Pro license. Get one at
https://wisdomlayer.ai/pricing.

For Free-tier examples that work without a license, see:
  - basic_agent.py
  - memory_example.py
  - quickstart_cloud.py
  - quickstart_local.py
  - mcp_quickstart.py
  - langgraph_quickstart.py

Usage:
    pip install "wisdom-layer[anthropic]"
    ANTHROPIC_API_KEY=sk-ant-... \\
        WISDOM_LAYER_LICENSE=wl_pro_... \\
        python critic_example.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("critic_example")
logger.setLevel(logging.INFO)


async def main() -> None:
    from wisdom_layer import AgentConfig, WisdomAgent
    from wisdom_layer.llm.anthropic import AnthropicAdapter
    from wisdom_layer.storage import SQLiteBackend

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.error("Set ANTHROPIC_API_KEY to run this example")
        sys.exit(1)

    license_key = os.environ.get("WISDOM_LAYER_LICENSE")
    if not license_key:
        logger.error(
            "This example requires a Pro license.\n"
            "Get one at https://wisdomlayer.ai/pricing\n\n"
            "Then re-run with:\n"
            "    WISDOM_LAYER_LICENSE=wl_pro_... python critic_example.py\n\n"
            "For Free-tier examples, see basic_agent.py, memory_example.py,\n"
            "quickstart_cloud.py, quickstart_local.py, mcp_quickstart.py,\n"
            "or langgraph_quickstart.py.",
        )
        sys.exit(1)

    llm = AnthropicAdapter(api_key=api_key)
    agent = WisdomAgent(
        agent_id="critic-demo",
        config=AgentConfig.for_dev(name="Critic Demo Agent", api_key=license_key),
        llm=llm,
        backend=SQLiteBackend(":memory:"),
    )
    await agent.initialize()

    # --- 1. Add behavioral directives ------------------------------
    directives = [
        "Always acknowledge customer emotion before discussing policy.",
        "Never share internal pricing formulas with customers.",
        "Recommend escalation to a human agent for legal questions.",
    ]
    for text in directives:
        d = await agent.directives.add(text)
        logger.info("Added directive: %s", d["id"])

    active = await agent.directives.active()
    logger.info("\n%d active directives", len(active))

    # --- 2. Find relevant directives for a context -----------------
    relevant = await agent.directives.relevant("upset customer refund", limit=2)
    logger.info("\nRelevant to 'upset customer refund':")
    for d in relevant:
        logger.info("  - %s", d["text"][:80])

    # --- 3. Evaluate a GOOD response --------------------------------
    good_response = (
        "I understand how frustrating this must be. Let me look into "
        "your refund right away and make sure we get this resolved."
    )
    review = await agent.critic.evaluate(
        good_response,
        context={"situation": "customer is upset about a broken product"},
    )
    logger.info("\nGood response review:")
    logger.info("  Risk level: %s", review["risk_level"])
    logger.info("  Pass through: %s", review["pass_through"])

    # --- 4. Evaluate a BAD response ---------------------------------
    bad_response = (
        "Per our policy section 4.2, items must be returned within "
        "14 business days. The restocking fee is 15%."
    )
    review = await agent.critic.evaluate(
        bad_response,
        context={"situation": "customer is upset about a broken product"},
    )
    logger.info("\nBad response review:")
    logger.info("  Risk level: %s", review["risk_level"])
    logger.info("  Pass through: %s", review["pass_through"])
    if review.get("flags"):
        logger.info("  Flags:")
        for flag in review["flags"]:
            logger.info("    - %s", flag)

    # --- 5. Evaluate a RISKY response (legal question) ---------------
    risky_response = (
        "Based on consumer protection law, you're entitled to a full "
        "refund plus damages. I can process that now."
    )
    review = await agent.critic.evaluate(
        risky_response,
        context={"situation": "customer asking about legal rights"},
    )
    logger.info("\nRisky response review:")
    logger.info("  Risk level: %s", review["risk_level"])
    logger.info("  Pass through: %s", review["pass_through"])
    if review.get("flags"):
        logger.info("  Flags:")
        for flag in review["flags"]:
            logger.info("    - %s", flag)

    # --- 6. Run a full coherence audit ------------------------------
    audit = await agent.critic.audit()
    logger.info("\nCoherence audit:")
    logger.info("  %s", audit)

    await agent.close()
    logger.info("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
