"""ReAct (Reasoning + Acting) agent graph.

Structure:
    START -> llm -> should_continue -> tools -> llm (loop)
                                    -> END

Design notes:
    - `should_continue` and `tool_node` are standalone importable functions.
    - Phase 04 replaces `tool_node` with MCP gateway routing.
    - Phase 06 wraps `should_continue` with HITL interrupt logic.
"""

from typing import Any

from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph


class AgentState(MessagesState):
    """Extended state that carries CopilotKit tools and context."""

    tools: list[dict[str, Any]]
    copilotkit: dict[str, Any]


def _build_llm(config: dict) -> ChatOpenAI:
    from app.core.config import settings

    model_cfg = config.get("model", {})
    return ChatOpenAI(
        model=model_cfg.get("model_id", "gpt-5.4"),
        temperature=model_cfg.get("temperature", 0.7),
        max_tokens=model_cfg.get("max_tokens", 4096),
        api_key=settings.OPENAI_API_KEY or None,
        base_url=settings.OPENAI_BASE_URL or None,
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


def _get_tool_name(tool: dict[str, Any]) -> str | None:
    """Return a stable tool name across OpenAI and AG-UI tool shapes."""
    if tool.get("type") == "function":
        function = tool.get("function")
        if isinstance(function, dict):
            name = function.get("name")
            if isinstance(name, str) and name:
                return name

    name = tool.get("name")
    if isinstance(name, str) and name:
        return name
    return None


def _get_bound_tools(state: AgentState) -> list[dict[str, Any]]:
    """Combine built-in tools with CopilotKit-provided frontend actions."""
    tools: list[dict[str, Any]] = [*MOCK_TOOLS]
    raw_tools = state.get("tools") or []
    if isinstance(raw_tools, list):
        tools.extend(tool for tool in raw_tools if isinstance(tool, dict))

    unique_tools: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for tool in tools:
        tool_name = _get_tool_name(tool)
        if tool_name is not None:
            if tool_name in seen_names:
                continue
            seen_names.add(tool_name)
        unique_tools.append(tool)
    return unique_tools


# --------------- Graph nodes ---------------


async def llm_node(state: AgentState, config: RunnableConfig) -> dict:
    """Call LLM — may produce tool calls."""
    agent_config = config.get("configurable", {}).get("agent_config", {})
    system_prompt = agent_config.get("system_prompt", "You are a helpful assistant.")

    llm = _build_llm(agent_config)
    llm_with_tools = llm.bind_tools(_get_bound_tools(state))

    messages = [SystemMessage(content=system_prompt), *state["messages"]]
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}


async def tool_node(state: AgentState) -> dict:
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


def should_continue(state: AgentState) -> str:
    """Route: tool calls -> 'tools' node, otherwise -> END.

    Phase 06 will wrap this to add HITL interrupt before tool execution.
    """
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


# --------------- Graph builder ---------------


def build_react_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("llm", llm_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "llm")
    graph.add_conditional_edges("llm", should_continue, ["tools", END])
    graph.add_edge("tools", "llm")
    return graph
