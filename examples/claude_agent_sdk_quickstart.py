"""Wisdom Layer SDK — Claude Agent SDK Quickstart.

Shows how to add persistent, compounding memory to an agent built with
Anthropic's Claude Agent SDK. The pattern is:

  1. Recall relevant memories + directives (Wisdom Layer)
  2. Inject them into the system prompt
  3. Run the agent via query() — tools handled automatically
  4. Capture the result for future recall (Wisdom Layer)

This example demonstrates Pro-tier features (critic evaluation, dream
cycles). It requires a Pro license. Get one at
https://wisdomlayer.ai/pricing.

For Free-tier examples that work without a license, see:
  - basic_agent.py
  - memory_example.py
  - quickstart_cloud.py

Usage:
    pip install claude-agent-sdk "wisdom-layer[anthropic]"
    ANTHROPIC_API_KEY=sk-ant-... \\
        WISDOM_LAYER_LICENSE=wl_pro_... \\
        python claude_agent_sdk_quickstart.py

The agent's database persists at ~/.wisdom-layer/claude-agent.db — run
this script multiple times to see the agent accumulate knowledge.

See docs/claude-agent-sdk.md for the full integration guide.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from claude_agent_sdk import (
    ClaudeAgentOptions,
    InMemorySessionStore,
    ResultMessage,
    query,
)

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("claude_agent")
logger.setLevel(logging.INFO)

DB_DIR = Path.home() / ".wisdom-layer"
DB_PATH = DB_DIR / "claude-agent.db"

# Shared session store — the Agent SDK uses this to maintain conversational
# context across turns for the same session_id.
_session_store = InMemorySessionStore()


async def respond(
    agent: object,
    user_message: str,
    *,
    session_id: str,
    api_key: str,
    model: str,
) -> str:
    """Single turn: recall → inject into system_prompt → query() → capture."""
    from wisdom_layer import WisdomAgent

    assert isinstance(agent, WisdomAgent)

    # 1. Recall relevant memories and directives
    memories = await agent.memory.search(user_message, limit=5)
    directives = await agent.directives.relevant(user_message, limit=3)

    # 2. Format memory as clean Q→A pairs (content is a dict, not a string)
    memory_lines: list[str] = []
    for m in memories:
        content = m.get("content", {})
        if isinstance(content, dict):
            user_turn = content.get("user", "")
            assistant_turn = content.get("assistant", "")
            if user_turn and assistant_turn:
                memory_lines.append(
                    f"- Q: {user_turn[:120]} → A: {assistant_turn[:200]}"
                )
        else:
            memory_lines.append(f"- {str(content)[:200]}")

    directive_lines = [f"- {d['text']}" for d in directives if d.get("text")]

    system = "You are a helpful research assistant."
    if memory_lines:
        system += "\n\nRelevant past context from memory:\n" + "\n".join(memory_lines)
    if directive_lines:
        system += "\n\nBehavioural rules to follow:\n" + "\n".join(directive_lines)

    # 3. Run the Claude Agent SDK — WebSearch/WebFetch available as tools
    reply = ""
    async for msg in query(
        prompt=user_message,
        options=ClaudeAgentOptions(
            system_prompt=system,
            allowed_tools=["WebSearch", "WebFetch"],
            model=model,
            max_turns=10,
            permission_mode="bypassPermissions",
            session_id=session_id,
            session_store=_session_store,
            # Pin the API key so the subprocess is immune to shell env pollution.
            env={"ANTHROPIC_API_KEY": api_key},
        ),
    ):
        if isinstance(msg, ResultMessage):
            if msg.is_error:
                errors = "; ".join(msg.errors or ["unknown agent error"])
                raise RuntimeError(f"Agent error: {errors}")
            reply = msg.result or ""
            logger.info(
                "  [agent sdk] turns=%d  cost=$%.4f",
                msg.num_turns,
                msg.total_cost_usd or 0.0,
            )

    # 4. Capture the completed turn for future recall
    await agent.memory.capture(
        "conversation",
        {"user": user_message, "assistant": reply},
    )

    # 5. Critic evaluation against learned directives (Pro)
    review = await agent.critic.evaluate(reply, context={"query": user_message})
    if not review["pass_through"]:
        logger.warning(
            "  [critic] risk=%s: %s",
            review["risk_level"],
            review.get("reasoning", ""),
        )

    return reply


async def main() -> None:
    from wisdom_layer import AgentConfig, WisdomAgent
    from wisdom_layer.llm.anthropic import AnthropicAdapter
    from wisdom_layer.storage import SQLiteBackend

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.error("Set ANTHROPIC_API_KEY to run this demo")
        sys.exit(1)

    license_key = os.environ.get("WISDOM_LAYER_LICENSE", "")
    if not license_key:
        logger.error(
            "This example requires a Pro license.\n"
            "Get one at https://wisdomlayer.ai/pricing\n\n"
            "Then re-run with:\n"
            "    WISDOM_LAYER_LICENSE=wl_pro_... python claude_agent_sdk_quickstart.py\n\n"
            "For Free-tier examples, see basic_agent.py or quickstart_cloud.py.",
        )
        sys.exit(1)

    model = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

    # --- Set up Wisdom Layer -----------------------------------------------
    llm = AnthropicAdapter(api_key=api_key)
    DB_DIR.mkdir(parents=True, exist_ok=True)
    backend = SQLiteBackend(str(DB_PATH))

    agent = WisdomAgent(
        agent_id="claude-agent-001",
        config=AgentConfig.for_dev(
            name="Research Assistant",
            role="Technical research specialist",
            api_key=license_key,
        ),
        llm=llm,
        backend=backend,
    )
    await agent.initialize()
    logger.info("Agent '%s' ready (tier: %s)\n", agent.name, agent.tier.value)

    session_id = "research-quickstart-001"

    # --- Simulate a multi-turn session -------------------------------------
    turns = [
        "I'm building a vector search system with pgvector. What are the key tradeoffs?",
        "What embedding models work well with pgvector?",
        "What were the main tradeoffs you mentioned earlier?",
    ]

    for user_msg in turns:
        logger.info("User: %s", user_msg)
        reply = await respond(
            agent,
            user_msg,
            session_id=session_id,
            api_key=api_key,
            model=model,
        )
        logger.info(
            "Assistant: %s\n",
            reply[:200] + "..." if len(reply) > 200 else reply,
        )

    # --- Dream cycle (reconsolidate + evolve directives) -------------------
    logger.info("Triggering dream cycle...")
    report = await agent.dreams.trigger()
    logger.info(
        "Dream cycle: status=%s, steps=%d",
        report["status"],
        len(report["steps"]),
    )
    for step in report["steps"]:
        logger.info("  %s → %s", step["name"], step["status"])

    # --- Agent health after the session ------------------------------------
    health = await agent.health()
    total_memories = (
        health.memory_stats.stream_count + health.memory_stats.consolidated_count
    )
    logger.info(
        "\nSession complete: %d memories, wisdom_score=%.2f (%s)",
        total_memories,
        health.wisdom_score or 0.0,
        health.cognitive_health,
    )

    await backend.close()
    logger.info("Database saved at %s", DB_PATH)
    logger.info("Run this script again — the agent will remember this conversation.")


if __name__ == "__main__":
    asyncio.run(main())
