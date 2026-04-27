# Claude Agent SDK Integration

Add persistent memory and compounding wisdom to agents built with
Anthropic's [Claude Agent SDK](https://docs.anthropic.com/en/docs/claude-code/sdk).
Your agent retains knowledge across sessions, learns behavioural rules
from experience, and self-improves through autonomous reflection.

---

## Install

```bash
pip install claude-agent-sdk "wisdom-layer[anthropic]"
```

---

## Basic Integration

The Wisdom Layer wraps `query()` calls: recall relevant memories before
each turn, inject them into the system prompt, then capture the result
afterward. The Agent SDK handles tool execution; the Wisdom Layer
handles persistent memory.

```python
import asyncio
import os
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, InMemorySessionStore
from wisdom_layer import WisdomAgent, AgentConfig
from wisdom_layer.llm.anthropic import AnthropicAdapter
from wisdom_layer.storage import SQLiteBackend


async def main() -> None:
    # 1. Set up Wisdom Layer
    llm = AnthropicAdapter(api_key=os.environ["ANTHROPIC_API_KEY"])
    agent = WisdomAgent(
        agent_id="research-agent-001",
        config=AgentConfig.for_prod(
            name="Research Assistant",
            role="Technical research specialist",
            # Critic + dreams require Pro. Get a key at
            # https://wisdomlayer.ai/pricing.
            api_key=os.environ.get("WISDOM_LAYER_LICENSE", ""),
        ),
        llm=llm,
        backend=SQLiteBackend("./research_agent.db"),
    )
    await agent.initialize()

    # 2. Session store — Agent SDK uses this to continue conversations
    session_store = InMemorySessionStore()
    session_id = "research-session-001"

    user_message = "What were the key findings from last week's analysis?"

    # 3. Recall relevant memories and directives
    memories = await agent.memory.search(user_message, limit=5)
    directives = await agent.directives.relevant(user_message, limit=3)

    # 4. Build context-augmented system prompt
    memory_lines = []
    for m in memories:
        content = m.get("content", {})
        if isinstance(content, dict):
            user_turn = content.get("user", "")
            assistant_turn = content.get("assistant", "")
            if user_turn and assistant_turn:
                memory_lines.append(f"- Q: {user_turn[:120]} → A: {assistant_turn[:200]}")
        else:
            memory_lines.append(f"- {str(content)[:200]}")

    directive_lines = [f"- {d['text']}" for d in directives if d.get("text")]

    system = "You are a research assistant."
    if memory_lines:
        system += "\n\nRelevant past context from memory:\n" + "\n".join(memory_lines)
    if directive_lines:
        system += "\n\nBehavioural principles to follow:\n" + "\n".join(directive_lines)

    # 5. Run the Claude Agent SDK — tools are handled automatically
    reply = ""
    async for msg in query(
        prompt=user_message,
        options=ClaudeAgentOptions(
            system_prompt=system,
            allowed_tools=["WebSearch", "WebFetch"],
            max_turns=10,
            permission_mode="bypassPermissions",
            session_id=session_id,
            session_store=session_store,
        ),
    ):
        if isinstance(msg, ResultMessage):
            if msg.is_error:
                raise RuntimeError("; ".join(msg.errors or ["agent error"]))
            reply = msg.result or ""

    # 6. Capture the completed turn for future recall
    await agent.memory.capture(
        "conversation",
        {"user": user_message, "assistant": reply},
    )

    print(reply)
    await agent.close()


asyncio.run(main())
```

---

## How the Pieces Fit

```
User message
    ↓
agent.memory.search()       ─── "What have I seen before that's relevant?"
agent.directives.relevant() ─── "What rules have I learned to follow?"
    ↓
Augment system_prompt with recalled context + principles
    ↓
query(prompt, ClaudeAgentOptions(system_prompt=..., allowed_tools=[...]))
    ↓
Claude Agent SDK runs the agent loop:
  → tool calls (WebSearch, WebFetch, Bash, …) handled automatically
  → yields ResultMessage when done
    ↓
agent.memory.capture(turn)  ─── "Remember this for next time"
```

---

## Multi-Turn Conversations

Pass a `session_id` and `session_store` to maintain conversational
context across turns. The Agent SDK handles within-session continuity;
the Wisdom Layer handles long-term cross-session memory.

```python
from claude_agent_sdk import InMemorySessionStore

session_store = InMemorySessionStore()  # persist for process lifetime
session_id = f"user-{user_id}"         # one session per user (or per user+role)

async for msg in query(
    prompt=user_message,
    options=ClaudeAgentOptions(
        system_prompt=system,           # Wisdom Layer recall injected here
        session_id=session_id,
        session_store=session_store,
        allowed_tools=["WebSearch", "WebFetch"],
        permission_mode="bypassPermissions",
    ),
):
    if isinstance(msg, ResultMessage):
        reply = msg.result or ""
```

---

## Capturing Tool Results

Tool results flow through the Agent SDK automatically. Capture the
completed turn after `ResultMessage` so the agent builds domain
knowledge from what it researched:

```python
async for msg in query(prompt=user_message, options=options):
    if isinstance(msg, ResultMessage):
        reply = msg.result or ""

# Capture the full turn — includes the effect of any tool calls made
await agent.memory.capture(
    "conversation",
    {"user": user_message, "assistant": reply},
)
```

---

## Adding Directives from Experience

As your agent handles interactions, it can learn behavioural rules that
persist and improve future responses. Mutating directives (`add`,
`promote`, `deactivate`, `reinforce`) requires a Pro key; read-only
methods (`get`, `active`, `all`, `relevant`) are Free.

```python
# Pro: add a rule learned from this interaction
await agent.directives.add(
    "When discussing research findings, always cite the source "
    "document and page number."
)

# Free: read-only retrieval for prompt injection (used above)
directives = await agent.directives.relevant("research findings")
```

---

## Scheduled Reflection

Set up periodic dream cycles so the agent consolidates its experience
into lasting wisdom:

```python
from datetime import time

# Schedule nightly reflection at 3 AM (Pro)
await agent.dreams.schedule(interval_hours=24, at=time(3, 0))

# Or trigger manually after a batch of interactions (Pro)
report = await agent.dreams.trigger()
# report keys: cycle_id, status, steps, started_at, completed_at
print(f"Dream cycle: {report['status']} ({len(report['steps'])} steps)")

# Check the resulting health score
health = await agent.health()
print(f"Wisdom score: {health.wisdom_score:.2f} ({health.cognitive_health})")
```

---

## Production Pattern: Train Then Lock

```python
# Development: agent learns from every interaction
dev_agent = WisdomAgent(
    agent_id="research-v2",
    config=AgentConfig.for_dev(
        name="Research Agent",
        api_key=os.environ["WISDOM_LAYER_LICENSE"],
    ),
    llm=llm, backend=backend,
)
# ... capture memories, add directives, run dream cycles ...

# Production: accumulated wisdom frozen, no further drift
prod_agent = WisdomAgent(
    agent_id="research-v2",          # same ID = same wisdom
    config=AgentConfig.template_mode(
        name="Research Agent",
        api_key=os.environ["WISDOM_LAYER_LICENSE"],
        directives=["Rule 1", "Rule 2"],
    ),
    llm=llm, backend=backend,
)
# memory.search() works; capture/directives/dreams are blocked
```

---

## Monitoring

```python
# Health check
health = await agent.health()
print(health.wisdom_score)       # 0.0-1.0
print(health.cognitive_health)   # healthy / stagnant / drifting / overloaded

# Cost tracking
cost = await agent.cost.summary(window="7d")
print(f"${cost.total_usd:.4f} over {cost.total_tokens} tokens")

# Provenance
chain = await agent.provenance.trace(memory_id)
```

---

## Next Steps

- [Quickstart](quickstart.md) — full walkthrough
- [Integration Guide](integration-guide.md) — production patterns
- [API Reference](api-reference.md) — full public surface
- [examples/claude_agent_sdk_quickstart.py](../examples/claude_agent_sdk_quickstart.py) — runnable example
