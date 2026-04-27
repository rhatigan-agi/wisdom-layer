# LangGraph Integration

Add persistent, compounding memory to any LangGraph agent. Your
agent remembers past conversations, learns behavioral directives,
and improves over time.

> **Status:** The Quick Start (3-node) pattern is validated end-to-end
> against real `langgraph` + a compiled `StateGraph` — see the
> [`wisdom-graph`](https://github.com/rhatigan-agi/wisdom-graph) demo
> repo for the e2e test. All four Wisdom nodes
> (`WisdomRecallNode`, `WisdomCaptureNode`, `WisdomDreamNode`,
> `WisdomDirectivesNode`) plus the `WisdomStore` and
> `WisdomLayerMemory` helpers have full unit-test coverage in the
> SDK suite. The **Canonical Pattern** example below (tools +
> `bind_tools` + conditional edges) is reference code: the shape
> is API-correct against LangGraph's public surface, but the
> tool-using loop is not yet exercised in CI.

---

## LangChain vs LangGraph

LangChain ships two distinct PyPI packages that are easy to confuse:

| Package | What it is | Wisdom Layer support |
|---|---|---|
| `langgraph` | Graph/state-machine runtime (`StateGraph`, nodes, edges) | **This page** |
| `langchain` | Primitives — `tool`, `AnyMessage`, `init_chat_model`, retrievers, chains | Used **inside** LangGraph; we don't ship a separate wrapper |

The official LangGraph quickstart imports from both — `langgraph.graph`
for the runtime plus `langchain.tools` / `langchain.messages` /
`langchain.chat_models` for the primitives. You'll do the same.

**Version note**: the `langchain.tools` / `langchain.messages` /
`langchain.chat_models` paths are LangChain **1.0+**. Pre-1.0 used
`langchain_core.tools` and `langchain_core.messages`. If you're on
`langchain<1.0`, swap the import roots.

---

## Install

```bash
pip install "wisdom-layer[langgraph,anthropic]"
export ANTHROPIC_API_KEY=sk-ant-...
```

---

## Quick Start — 3-Node Graph

The simplest integration: **recall → LLM → capture**. No tools, no
conditional routing — just a linear pipe with persistent memory
wedged in.

```python
import asyncio
import os
from typing import Any
from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph

from wisdom_layer.agent import WisdomAgent
from wisdom_layer.config import AgentConfig
from wisdom_layer.storage.sqlite import SQLiteBackend
from wisdom_layer.llm.anthropic import AnthropicAdapter
from wisdom_layer.integration.langgraph import (
    WisdomCaptureNode,
    WisdomRecallNode,
)


# 1. Define your graph state
class AgentState(TypedDict):
    messages: list[dict[str, str]]
    wisdom_context: list[dict[str, Any]]


# 2. Create the Wisdom Layer agent
llm = AnthropicAdapter(api_key=os.environ["ANTHROPIC_API_KEY"])
backend = SQLiteBackend("my_agent.db")  # embedder auto-wired from llm at agent.initialize()
config = AgentConfig(name="My Agent", role="Helpful assistant")
agent = WisdomAgent(agent_id="my-agent", config=config, llm=llm, backend=backend)


# 3. Your LLM node uses wisdom context
async def call_llm(state: AgentState) -> dict[str, Any]:
    wisdom = state.get("wisdom_context", [])
    context = "\n".join(f"- {m['content']}" for m in wisdom) if wisdom else ""
    system = f"You are a helpful assistant.\n\nRelevant memories:\n{context}"
    user_msg = state["messages"][-1]["content"]

    response = await llm.generate(
        messages=[{"role": "user", "content": user_msg}],
        system=system,
    )
    return {"messages": [*state["messages"], {"role": "assistant", "content": response}]}


# 4. Build the graph
async def main():
    await agent.initialize()

    graph = StateGraph(AgentState)
    graph.add_node("recall", WisdomRecallNode(agent))
    graph.add_node("llm", call_llm)
    graph.add_node("capture", WisdomCaptureNode(agent))

    graph.add_edge(START, "recall")
    graph.add_edge("recall", "llm")
    graph.add_edge("llm", "capture")
    graph.add_edge("capture", END)

    app = graph.compile()

    result = await app.ainvoke({
        "messages": [{"role": "user", "content": "Hello, I'm building a SaaS product"}],
        "wisdom_context": [],
    })
    print(result["messages"][-1]["content"])

asyncio.run(main())
```

---

## Canonical Pattern — Tool-Using Agent Loop

The quickstart above skips tools and conditional routing for
brevity. The pattern below mirrors LangGraph's official quickstart
shape (`langchain.messages` + `@tool` + `bind_tools` +
`add_conditional_edges`) with Wisdom Layer wedged in around the
loop:

```python
import asyncio
import operator
import os
from typing import Annotated, Literal

from typing_extensions import TypedDict

from langchain.chat_models import init_chat_model
from langchain.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain.tools import tool
from langgraph.graph import END, START, StateGraph

from wisdom_layer.agent import WisdomAgent
from wisdom_layer.config import AgentConfig
from wisdom_layer.integration.langgraph import (
    WisdomCaptureNode,
    WisdomDirectivesNode,
    WisdomRecallNode,
)
from wisdom_layer.llm.anthropic import AnthropicAdapter
from wisdom_layer.storage.sqlite import SQLiteBackend


# 1. State uses LangChain message objects with the canonical reducer.
class State(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    wisdom_context: list[dict]
    wisdom_directives: list[str]


# 2. Tools — same as the official quickstart.
@tool
def add(a: int, b: int) -> int:
    """Add a and b."""
    return a + b


@tool
def multiply(a: int, b: int) -> int:
    """Multiply a and b."""
    return a * b


tools = [add, multiply]
tools_by_name = {t.name: t for t in tools}

# 3. The model used by LangGraph nodes (separate from the adapter
#    Wisdom uses internally for critic + dreams).
model = init_chat_model("claude-sonnet-4-6", temperature=0).bind_tools(tools)


# 4. Wisdom Layer agent — its OWN adapter for critic + dreams.
wisdom = WisdomAgent(
    agent_id="calculator-agent",
    config=AgentConfig.for_prod(
        name="Calculator",
        role="Arithmetic specialist",
        api_key=os.environ["WISDOM_LAYER_LICENSE"],
    ),
    llm=AnthropicAdapter(api_key=os.environ["ANTHROPIC_API_KEY"]),
    backend=SQLiteBackend("./calc.db"),
)


# 5. LLM node — folds wisdom context + directives into the system prompt.
def llm_call(state: State) -> dict:
    memory_block = "\n".join(f"- {m['content']}" for m in state.get("wisdom_context", []))
    directive_block = "\n".join(f"- {d}" for d in state.get("wisdom_directives", []))

    system = SystemMessage(content=f"""You are a calculator agent.

Relevant memories:
{memory_block}

Learned rules:
{directive_block}
""")
    return {"messages": [model.invoke([system] + state["messages"])]}


# 6. Tool node.
def tool_node(state: State) -> dict:
    last = state["messages"][-1]
    results = []
    for tc in last.tool_calls:
        observation = tools_by_name[tc["name"]].invoke(tc["args"])
        results.append(ToolMessage(content=str(observation), tool_call_id=tc["id"]))
    return {"messages": results}


# 7. Conditional edge.
def should_continue(state: State) -> Literal["tool_node", "capture"]:
    return "tool_node" if state["messages"][-1].tool_calls else "capture"


async def main() -> None:
    await wisdom.initialize()

    graph = StateGraph(State)
    graph.add_node("recall", WisdomRecallNode(wisdom))
    graph.add_node("directives", WisdomDirectivesNode(wisdom))
    graph.add_node("llm_call", llm_call)
    graph.add_node("tool_node", tool_node)
    graph.add_node("capture", WisdomCaptureNode(wisdom))

    graph.add_edge(START, "recall")
    graph.add_edge("recall", "directives")
    graph.add_edge("directives", "llm_call")
    graph.add_conditional_edges("llm_call", should_continue, ["tool_node", "capture"])
    graph.add_edge("tool_node", "llm_call")
    graph.add_edge("capture", END)

    app = graph.compile()

    result = await app.ainvoke({
        "messages": [HumanMessage(content="What is (3 + 4) * 5?")],
        "wisdom_context": [],
        "wisdom_directives": [],
    })
    for m in result["messages"]:
        m.pretty_print()

    await wisdom.close()


if __name__ == "__main__":
    asyncio.run(main())
```

The Wisdom nodes work transparently with both raw dict messages
(quickstart) and LangChain message objects (this example) — the
extraction helpers duck-type both shapes.

---

## Why We Bypass `init_chat_model` in Wisdom Layer

You'll notice the calculator example uses `init_chat_model(...)`
**inside** LangGraph nodes, but the `WisdomAgent` is constructed
with a separate `AnthropicAdapter`. That's deliberate:

- **LangGraph's model call** owns the agent loop, tool binding, and
  message formatting. `init_chat_model` is the right tool there.
- **Wisdom Layer's adapter** owns the model calls Wisdom makes
  internally — for the critic, dream cycles, and journal synthesis.
  Routing those through `BaseLLMAdapter` keeps cost tracking, budget
  guards, and provenance attached to the same call path.

Using a single LangChain chat model for both would lose Wisdom
Layer's per-call cost ledger and budget enforcement. Two adapters,
one per concern, is the cleaner separation.

---

## Available Nodes

### `WisdomRecallNode`

Searches wisdom memory and writes results to state.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `agent` | required | Initialized `WisdomAgent` |
| `limit` | `5` | Max memories to retrieve |
| `context_key` | `"wisdom_context"` | State key for results |
| `message_key` | `"messages"` | State key to read query from |

The node extracts the last human message from `messages`, searches
the agent's three-tier memory, and writes results to `wisdom_context`.

### `WisdomCaptureNode`

Captures the latest interaction into wisdom memory.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `agent` | required | Initialized `WisdomAgent` |
| `event_type` | `"interaction"` | Memory event type |
| `message_key` | `"messages"` | State key to read from |

Extracts the last human/AI exchange from `messages` and stores it
as a memory. Over time, these memories get consolidated, form
directives, and compound into wisdom.

### `WisdomDreamNode`

Triggers a dream cycle (reflection pipeline).

| Parameter | Default | Description |
|-----------|---------|-------------|
| `agent` | required | Initialized `WisdomAgent` |
| `result_key` | `"dream_result"` | State key for results |

Runs the full 5-step pipeline: consolidate → evolve directives →
audit coherence → decay → journal synthesis. Use this in scheduled
graphs or end-of-session flows.

### `WisdomDirectivesNode`

Retrieves active behavioral directives for prompt injection.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `agent` | required | Initialized `WisdomAgent` |
| `context_key` | `"wisdom_directives"` | State key for results |

Returns a list of directive text strings. Inject these into your
system prompt so the LLM follows learned behavioral rules.

---

## What Happens Over Time

1. **Day 1**: The agent captures interactions as stream memories
2. **After a dream cycle**: Memories consolidate into patterns,
   behavioral directives emerge
3. **Ongoing**: Directives get reinforced or decayed based on usage,
   the agent's wisdom score improves, responses get better

---

## Full Example

See [`examples/langgraph_quickstart.py`](../examples/langgraph_quickstart.py)
for a complete runnable demo with a multi-turn conversation.
