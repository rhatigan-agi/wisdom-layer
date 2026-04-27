# OpenAI Agents SDK Integration

Add persistent, compounding memory to agents built with the OpenAI
Agents SDK (`openai-agents`).

> **Status: reference only.** A native, tested wrapper is in active
> development. The patterns below show how to wire Wisdom Layer
> alongside the Agents SDK today, but they have **not been validated
> in CI** — treat this page as a starting point, not a contract.
> The native integration will ship with full test coverage and a
> dedicated quickstart.

---

## Two Different SDKs

OpenAI ships two distinct Python packages, and they're easy to
confuse:

| Package | Purpose | Wisdom Layer support |
|---|---|---|
| `openai` | Direct API client (`chat.completions`, `responses`, embeddings) | `OpenAIAdapter` — **available today** |
| `openai-agents` | Agent framework with `Agent`, `Runner`, tools, handoffs | Native wrapper **coming soon** (this page) |

The `pip install "wisdom-layer[openai]"` extra below pulls in the
**client** SDK — that's what `OpenAIAdapter` calls. If you're using
the Agents SDK, install both packages.

---

## Install

```bash
pip install "wisdom-layer[openai]" openai-agents
export OPENAI_API_KEY=sk-...
```

---

## Reference: Wisdom Layer + Agents SDK

The Wisdom Layer sits **alongside** your Agents SDK code. The Agents
SDK owns the model call and the run loop; Wisdom Layer owns memory,
directives, and reflection. You recall before each run and capture
after.

```python
import asyncio
import os

from agents import Agent, Runner
from wisdom_layer import WisdomAgent, AgentConfig
from wisdom_layer.llm.openai import OpenAIAdapter
from wisdom_layer.storage import SQLiteBackend


async def main() -> None:
    # 1. Wisdom Layer holds memory + directives + reflection.
    #    The OpenAIAdapter here is what Wisdom uses internally for
    #    its critic and dream cycles -- separate from the model call
    #    the Agents SDK makes inside Runner.run().
    wisdom = WisdomAgent(
        agent_id="research-assistant-001",
        config=AgentConfig.for_prod(
            name="Research Assistant",
            role="Technical research specialist",
            # Critic + dreams require Pro. https://wisdomlayer.ai/pricing
            api_key=os.environ["WISDOM_LAYER_LICENSE"],
        ),
        llm=OpenAIAdapter(api_key=os.environ["OPENAI_API_KEY"]),
        backend=SQLiteBackend("./openai_agent.db"),
    )
    await wisdom.initialize()

    user_message = "What were the key findings from last week's analysis?"

    # 2. Recall relevant memories + directives before the run.
    memories = await wisdom.memory.search(user_message, limit=5)
    directives = await wisdom.directives.relevant(user_message)
    memory_block = "\n".join(f"- {m['content']}" for m in memories)
    directive_block = "\n".join(f"- {d['text']}" for d in directives)

    # 3. Fold them into the Agents SDK agent's instructions.
    instructions = f"""You answer research questions clearly and concisely.

Relevant memories:
{memory_block}

Learned rules:
{directive_block}
"""

    agent = Agent(
        name="Research tutor",
        instructions=instructions,
        model="gpt-4.1-mini",
    )

    # 4. Run the Agents SDK normally.
    result = await Runner.run(agent, user_message)
    print(result.final_output)

    # 5. Capture the interaction for future recall.
    await wisdom.memory.capture(
        "conversation",
        {"user": user_message, "assistant": result.final_output},
    )

    await wisdom.close()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Function Tools

Capture tool results into memory so the agent builds domain
knowledge over time. Wrap the body of any `@function_tool`:

```python
from agents import function_tool


@function_tool
async def lookup_customer(customer_id: str) -> str:
    """Fetch a customer record."""
    record = await db.fetch_customer(customer_id)
    await wisdom.memory.capture(
        "tool_result",
        {"tool": "lookup_customer", "input": {"id": customer_id}, "result": record},
        emotional_intensity=0.2,
    )
    return record
```

---

## Handoffs Between Specialists

When the triage agent hands off to a specialist, the Agents SDK
returns `result.last_agent` so you know which one produced the
reply. Tag captures with that agent's name to keep memory
attributable across specialists:

```python
result = await Runner.run(triage_agent, user_message)

await wisdom.memory.capture(
    "conversation",
    {
        "user": user_message,
        "assistant": result.final_output,
        "answered_by": result.last_agent.name,
    },
)
```

If you want each specialist to have its own memory store, give each
one a separate `WisdomAgent(agent_id=...)` and route captures to the
matching instance based on `result.last_agent.name`.

---

## Periodic Reflection

Reflection runs the same way it does in any Wisdom Layer setup —
the Agents SDK isn't involved:

```python
# Manually trigger after a batch of interactions
report = await wisdom.dreams.trigger()

# Or schedule nightly
from datetime import time
await wisdom.dreams.schedule(interval_hours=24, at=time(3, 0))
```

---

## Caveats Until the Native Wrapper Ships

- **Streaming.** `Runner.run_streamed()` works, but the example above
  uses the non-streaming path. If you stream, capture from the final
  result event, not from individual deltas.
- **Sessions.** The Agents SDK `Session` object and Wisdom Layer's
  `agent.session(...)` are unrelated. You can use both — the Agents
  SDK session manages conversation state for the model; Wisdom
  sessions scope memory captures.
- **Approvals / interruptions.** If the Agents SDK pauses for human
  review, capture the resumption decision with
  `wisdom.memory.capture("approval", {...})` so the directive
  pipeline can learn from it.
- **Tracing.** Agents SDK traces appear in the OpenAI Traces
  dashboard. Wisdom Layer keeps its own provenance via
  `wisdom.provenance.trace(memory_id)`. They are independent.

---

## Get Notified

Sign up to be the first to know when the native wrapper ships:

**[Join the waitlist](https://wisdom-layer-newsletter.beehiiv.com/subscribe)** — one email when this lands, nothing else.

---

## Related Integrations

- [LangGraph](langgraph.md) — available now
- [Claude Agent SDK](claude-agent-sdk.md) — available now
- [MCP](mcp.md) — available now
