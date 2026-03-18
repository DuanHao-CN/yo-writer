"""ReAct (Reasoning + Acting) agent graph.

Structure:
    START -> llm -> should_continue -> tools -> llm (loop)
                                    -> END

Design notes:
    - `should_continue` and `tool_node` are standalone importable functions.
    - Phase 04: `tool_node` routes calls through FastMCP gateway.
    - Phase 06 wraps `should_continue` with HITL interrupt logic.
"""

import logging
from typing import Any

from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph

logger = logging.getLogger(__name__)

# MCP tool schemas are cached at module level after first fetch.
_mcp_tool_cache: list[dict[str, Any]] | None = None


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


async def _get_mcp_tools() -> list[dict[str, Any]]:
    """Fetch MCP gateway tool schemas, with module-level caching."""
    global _mcp_tool_cache
    if _mcp_tool_cache is None:
        from app.runtime.mcp_gateway import get_mcp_tool_schemas

        _mcp_tool_cache = await get_mcp_tool_schemas()
    return _mcp_tool_cache


async def _get_bound_tools(state: AgentState) -> list[dict[str, Any]]:
    """Combine MCP gateway tools with CopilotKit-provided frontend actions."""
    mcp_tools = await _get_mcp_tools()
    tools: list[dict[str, Any]] = [*mcp_tools]

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
    bound_tools = await _get_bound_tools(state)
    llm_with_tools = llm.bind_tools(bound_tools)

    messages = [SystemMessage(content=system_prompt), *state["messages"]]
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}


async def tool_node(state: AgentState) -> dict:
    """Execute tool calls via MCP gateway.

    Phase 06 wraps this with HITL interrupt logic.
    """
    from app.runtime.mcp_gateway import call_mcp_tool

    results: list[ToolMessage] = []
    last_message = state["messages"][-1]

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        try:
            content = await call_mcp_tool(tool_name, tool_args)
        except Exception as exc:
            logger.warning("Tool call failed: %s(%s) -> %s", tool_name, tool_args, exc)
            content = f"Error calling tool '{tool_name}': {exc}"

        results.append(
            ToolMessage(content=content, tool_call_id=tool_call["id"])
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
