"""ReAct agent graph with Human-in-the-Loop (HITL) patterns.

Structure: same as react.py (START -> llm -> should_continue -> tools -> llm loop)
but tool_node is replaced with tool_node_with_hitl that can pause execution for:
  - approval: human must approve/reject/edit before tool runs
  - review: tool runs first, human reviews/edits the output before continuing

Uses LangGraph interrupt() for checkpoint-based suspension.
"""

import json
import logging
from typing import Any

from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.runtime.graphs.react import (
    AgentState,
    entry_router,
    llm_node,
    should_continue,
)
from app.runtime.mcp_gateway import call_mcp_tool

logger = logging.getLogger(__name__)


async def tool_node_with_hitl(state: AgentState, config: RunnableConfig) -> dict:
    """Execute tool calls with optional HITL interrupt for approval or review."""
    agent_config = config.get("configurable", {}).get("agent_config", {})
    hitl_config = agent_config.get("hitl", {})
    require_approval: list[str] = hitl_config.get("require_approval", [])
    require_review: list[str] = hitl_config.get("require_review", [])

    results: list[ToolMessage] = []
    last_message = state["messages"][-1]

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_call_id = tool_call["id"]

        if tool_name in require_approval:
            result_msg = await _handle_approval(
                tool_name, tool_args, tool_call_id
            )
        elif tool_name in require_review:
            result_msg = await _handle_review(
                tool_name, tool_args, tool_call_id
            )
        else:
            result_msg = await _execute_tool(tool_name, tool_args, tool_call_id)

        results.append(result_msg)

    return {"messages": results}


async def _handle_approval(
    tool_name: str, tool_args: dict[str, Any], tool_call_id: str
) -> ToolMessage:
    """Interrupt for human approval before executing the tool."""
    resume_value = interrupt({
        "type": "approval",
        "tool_name": tool_name,
        "tool_args": tool_args,
        "tool_call_id": tool_call_id,
        "message": f"Tool '{tool_name}' requires approval before execution.",
    })

    # Parse resume value — may be dict or JSON string
    if isinstance(resume_value, str):
        resume_value = json.loads(resume_value)

    action = resume_value.get("action", "reject")

    if action == "reject":
        return ToolMessage(
            content=f"Tool '{tool_name}' was rejected by user.",
            tool_call_id=tool_call_id,
        )

    if action == "edit":
        tool_args = resume_value.get("edited_args", tool_args)

    # approve or edit → execute
    return await _execute_tool(tool_name, tool_args, tool_call_id)


async def _handle_review(
    tool_name: str, tool_args: dict[str, Any], tool_call_id: str
) -> ToolMessage:
    """Execute tool first, then interrupt for human review of the output."""
    result_msg = await _execute_tool(tool_name, tool_args, tool_call_id)
    original_output = result_msg.content

    resume_value = interrupt({
        "type": "review",
        "tool_name": tool_name,
        "original_output": original_output,
        "tool_call_id": tool_call_id,
        "message": f"Review the output of '{tool_name}' before continuing.",
    })

    # Parse resume value
    if isinstance(resume_value, str):
        resume_value = json.loads(resume_value)

    edited_output = resume_value.get("edited_output", original_output)
    return ToolMessage(content=edited_output, tool_call_id=tool_call_id)


async def _execute_tool(
    tool_name: str, tool_args: dict[str, Any], tool_call_id: str
) -> ToolMessage:
    """Execute a tool via MCP gateway."""
    try:
        content = await call_mcp_tool(tool_name, tool_args)
    except Exception as exc:
        logger.warning("Tool call failed: %s(%s) -> %s", tool_name, tool_args, exc)
        content = f"Error calling tool '{tool_name}': {exc}"

    return ToolMessage(content=content, tool_call_id=tool_call_id)


def build_react_hitl_graph() -> StateGraph:
    """Build ReAct graph with HITL-enabled tool node."""
    graph = StateGraph(AgentState)
    graph.add_node("llm", llm_node)
    graph.add_node("tools", tool_node_with_hitl)
    graph.add_conditional_edges(START, entry_router, ["llm", END])
    graph.add_conditional_edges("llm", should_continue, ["tools", END])
    graph.add_edge("tools", "llm")
    return graph
