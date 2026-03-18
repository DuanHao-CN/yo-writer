"""ReAct (Reasoning + Acting) agent graph.

Structure:
    START -> llm -> should_continue -> tools -> llm (loop)
                                    -> END

Design notes:
    - `should_continue` and `tool_node` are standalone importable functions.
    - Phase 04 replaces `tool_node` with MCP gateway routing.
    - Phase 06 wraps `should_continue` with HITL interrupt logic.
"""

from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph


def _build_llm(config: dict) -> ChatOpenAI:
    from app.core.config import settings

    model_cfg = config.get("model", {})
    return ChatOpenAI(
        model=model_cfg.get("model_id", "gpt-4o"),
        temperature=model_cfg.get("temperature", 0.7),
        max_tokens=model_cfg.get("max_tokens", 4096),
        api_key=settings.OPENAI_API_KEY or None,
    )


# --------------- Mock tools for Phase 02 ---------------

MOCK_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Perform basic arithmetic calculations",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression to evaluate",
                    }
                },
                "required": ["expression"],
            },
        },
    }
]


# --------------- Graph nodes ---------------


async def llm_node(state: MessagesState, config: RunnableConfig) -> dict:
    """Call LLM — may produce tool calls."""
    agent_config = config.get("configurable", {}).get("agent_config", {})
    system_prompt = agent_config.get("system_prompt", "You are a helpful assistant.")

    llm = _build_llm(agent_config)
    llm_with_tools = llm.bind_tools(MOCK_TOOLS)

    messages = [SystemMessage(content=system_prompt), *state["messages"]]
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}


async def tool_node(state: MessagesState) -> dict:
    """Execute tool calls — mock implementation for Phase 02.

    Phase 04 replaces this with real MCP gateway routing.
    Phase 06 wraps this with HITL interrupt logic.
    """
    results = []
    last_message = state["messages"][-1]
    for tool_call in last_message.tool_calls:
        results.append(
            ToolMessage(
                content=f"[Mock] Tool '{tool_call['name']}' called with {tool_call['args']}",
                tool_call_id=tool_call["id"],
            )
        )
    return {"messages": results}


def should_continue(state: MessagesState) -> str:
    """Route: tool calls -> 'tools' node, otherwise -> END.

    Phase 06 will wrap this to add HITL interrupt before tool execution.
    """
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


# --------------- Graph builder ---------------


def build_react_graph() -> StateGraph:
    graph = StateGraph(MessagesState)
    graph.add_node("llm", llm_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "llm")
    graph.add_conditional_edges("llm", should_continue, ["tools", END])
    graph.add_edge("tools", "llm")
    return graph
