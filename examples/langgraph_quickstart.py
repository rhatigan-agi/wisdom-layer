"""LangGraph + Wisdom Layer quickstart.

A simple 3-node graph: recall -> LLM -> capture.
The agent remembers past conversations and uses them to improve responses.

Requirements:
    pip install "wisdom-layer[langgraph,anthropic]"
    # Or swap anthropic for openai

Usage:
    ANTHROPIC_API_KEY=sk-ant-... python langgraph_quickstart.py
    # Or: OPENAI_API_KEY=sk-... python langgraph_quickstart.py
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from typing_extensions import TypedDict

from wisdom_layer.agent import WisdomAgent
from wisdom_layer.config import AgentConfig
from wisdom_layer.integration.langgraph import WisdomCaptureNode, WisdomRecallNode
from wisdom_layer.storage.sqlite import SQLiteBackend

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("langgraph_quickstart")
logger.setLevel(logging.INFO)


class AgentState(TypedDict):
    """State that flows through the graph."""

    messages: list[dict[str, str]]
    wisdom_context: list[dict[str, Any]]


def _create_llm() -> Any:
    """Auto-detect an LLM adapter from environment variables."""
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        from wisdom_layer.llm.anthropic import AnthropicAdapter

        return AnthropicAdapter(api_key=anthropic_key)

    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        from wisdom_layer.llm.openai import OpenAIAdapter

        return OpenAIAdapter(api_key=openai_key)

    raise RuntimeError("Set ANTHROPIC_API_KEY or OPENAI_API_KEY")


def make_llm_node(llm: Any):
    """Return a LangGraph node that calls the LLM with wisdom context."""

    async def call_llm(state: AgentState) -> dict[str, Any]:
        messages = state["messages"]
        wisdom = state.get("wisdom_context", [])

        context_block = ""
        if wisdom:
            memories = "\n".join(f"- {m['content']}" for m in wisdom)
            context_block = (
                f"\n\nRelevant memories from past conversations:\n{memories}\n"
                "Use these to give more personalized, contextual responses."
            )

        system = f"You are a helpful assistant.{context_block}"
        user_msg = messages[-1]["content"] if messages else ""

        response = await llm.generate(
            messages=[{"role": "user", "content": user_msg}],
            system=system,
        )

        return {
            "messages": [
                *messages,
                {"role": "assistant", "content": response},
            ],
        }

    return call_llm


async def main() -> None:
    """Run the LangGraph + Wisdom Layer demo."""
    from langgraph.graph import END, START, StateGraph

    llm = _create_llm()
    backend = SQLiteBackend("langgraph_demo.db")
    config = AgentConfig(name="LangGraph Demo", role="Helpful assistant")
    agent = WisdomAgent(agent_id="langgraph-demo", config=config, llm=llm, backend=backend)
    await agent.initialize()

    recall = WisdomRecallNode(agent)
    capture = WisdomCaptureNode(agent)

    graph = StateGraph(AgentState)
    graph.add_node("recall", recall)
    graph.add_node("llm", make_llm_node(llm))
    graph.add_node("capture", capture)

    graph.add_edge(START, "recall")
    graph.add_edge("recall", "llm")
    graph.add_edge("llm", "capture")
    graph.add_edge("capture", END)

    app = graph.compile()

    questions = [
        "My name is Alex and I'm building a SaaS product for dog walkers.",
        "What pricing model would you recommend for my product?",
        "What was my name and what am I building?",
    ]

    for q in questions:
        logger.info("\n%s", "=" * 60)
        logger.info("User: %s", q)
        result = await app.ainvoke({
            "messages": [{"role": "user", "content": q}],
            "wisdom_context": [],
        })
        response = result["messages"][-1]["content"]
        logger.info("Assistant: %s", response[:500])

    logger.info("\n%s", "=" * 60)
    logger.info("Searching wisdom memory for 'Alex'...")
    memories = await agent.memory.search("Alex SaaS dog walkers", limit=3)
    for m in memories:
        logger.info("  - %s", str(m.get("content", m.get("text", "")))[:100])

    logger.info("\nDone! The agent now has persistent memory across sessions.")

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
