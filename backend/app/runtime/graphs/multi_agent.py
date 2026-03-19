"""Multi-Agent Supervisor graph.

Structure:
    START -> entry_router -> supervisor -> approve_delegation -> sub-agent -> supervisor (loop)
                                                              -> END (done)

Design notes:
    - Supervisor LLM decides which sub-agent to delegate to.
    - Delegation approval uses HITL interrupt so the user can approve/redirect/stop.
    - Three built-in sub-agents: researcher, coder, reviewer.
    - Each sub-agent uses LLM + bound tools (MCP gateway) with a role-specific prompt.
"""

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.runtime.graphs.react import (
    AgentState,
    _build_llm,
    _get_bound_tools,
    make_entry_router,
    tool_node,
)
from app.runtime.graphs.react_hitl import tool_node_with_hitl

logger = logging.getLogger(__name__)

AVAILABLE_AGENTS = ["researcher", "coder", "reviewer"]


class SupervisorState(AgentState):
    """Extended state for multi-agent supervisor graphs."""

    next_agent: str
    agent_outputs: dict[str, str]


SUPERVISOR_PROMPT = """You are a supervisor coordinating a team of specialist agents.

{agent_instructions}

Available agents:
- researcher: Searches for information, reads documents, gathers data
- coder: Writes code, fixes bugs, implements features
- reviewer: Reviews work quality, checks for errors, provides feedback

Based on the conversation and any previous agent outputs, decide which agent should handle the next step.

Return a JSON object with:
- "next_agent": one of "researcher", "coder", "reviewer", or "done"
- "task": a brief description of what the agent should do
- "reasoning": why you chose this agent

Example: {{"next_agent": "researcher", "task": "Find documentation on the API", "reasoning": "Need information before coding"}}

Previous agent outputs:
{agent_outputs}

Only return the JSON object, nothing else."""

AGENT_PROMPTS = {
    "researcher": """You are a research specialist. Your role is to search for information, read documents, and gather relevant data.

{agent_instructions}

Task from supervisor: {task}

Use the available tools to research thoroughly, then provide a clear summary of your findings.""",

    "coder": """You are a coding specialist. Your role is to write code, fix bugs, and implement features.

{agent_instructions}

Task from supervisor: {task}

Use the available tools as needed, then provide your code and explanation.""",

    "reviewer": """You are a review specialist. Your role is to review work quality, check for errors, and provide constructive feedback.

{agent_instructions}

Task from supervisor: {task}

Review the work done so far and provide detailed feedback.""",
}


def _get_agent_instructions(agent_config: dict) -> str:
    """Extract system prompt as additional instructions for advanced graph nodes."""
    prompt = agent_config.get("system_prompt", "")
    if prompt and prompt != "You are a helpful assistant.":
        return f"Additional instructions from agent configuration:\n{prompt}"
    return ""


def _select_tool_handler(agent_config: dict):
    """Return HITL-aware tool handler when approval/review lists are configured."""
    hitl = agent_config.get("hitl") or {}
    if hitl.get("require_approval") or hitl.get("require_review"):
        return tool_node_with_hitl
    return tool_node


# --------------- Graph nodes ---------------


async def supervisor_node(state: SupervisorState, config: RunnableConfig) -> dict:
    """Supervisor decides which sub-agent to delegate to next."""
    agent_config = config.get("configurable", {}).get("agent_config", {})
    llm = _build_llm(agent_config)

    agent_outputs = state.get("agent_outputs") or {}
    outputs_str = "\n".join(
        f"[{agent}]: {output}" for agent, output in agent_outputs.items()
    ) or "None yet."

    prompt = SUPERVISOR_PROMPT.format(
        agent_outputs=outputs_str,
        agent_instructions=_get_agent_instructions(agent_config),
    )
    messages = [SystemMessage(content=prompt), *state["messages"]]

    response = await llm.ainvoke(messages)
    content = response.content

    try:
        parsed = json.loads(content)
        next_agent = parsed.get("next_agent", "done")
        task = parsed.get("task", "")
        reasoning = parsed.get("reasoning", "")
    except (json.JSONDecodeError, AttributeError):
        next_agent = "done"
        task = ""
        reasoning = "Could not parse supervisor decision."

    if next_agent not in [*AVAILABLE_AGENTS, "done"]:
        next_agent = "done"

    msg = f"Supervisor decision: delegate to **{next_agent}**"
    if task:
        msg += f"\nTask: {task}"
    if reasoning:
        msg += f"\nReasoning: {reasoning}"

    return {
        "next_agent": next_agent,
        "messages": [AIMessage(content=msg)],
    }


async def delegation_approval_node(state: SupervisorState) -> dict:
    """Interrupt for human approval of delegation decision."""
    next_agent = state.get("next_agent", "done")

    if next_agent == "done":
        return {}

    resume_value = interrupt({
        "type": "delegation_approval",
        "next_agent": next_agent,
        "available_agents": AVAILABLE_AGENTS,
        "message": f"Supervisor wants to delegate to '{next_agent}'. Approve or redirect?",
    })

    if isinstance(resume_value, str):
        resume_value = json.loads(resume_value)

    action = resume_value.get("action", "stop")

    if action == "stop":
        return {
            "next_agent": "done",
            "messages": [AIMessage(content="Delegation stopped by user.")],
        }

    if action == "redirect":
        redirected = resume_value.get("redirect_to", next_agent)
        if redirected in AVAILABLE_AGENTS:
            return {"next_agent": redirected}
        return {"next_agent": "done"}

    # approve
    return {}


async def _run_sub_agent(
    state: SupervisorState, config: RunnableConfig, agent_name: str
) -> dict:
    """Run a sub-agent with role-specific prompt and tools."""
    agent_config = config.get("configurable", {}).get("agent_config", {})
    llm = _build_llm(agent_config)
    bound_tools = await _get_bound_tools(state)
    llm_with_tools = llm.bind_tools(bound_tools)
    handle_tools = _select_tool_handler(agent_config)

    # Extract task from last supervisor message
    task = ""
    for msg in reversed(state["messages"]):
        if hasattr(msg, "content") and "Task:" in msg.content:
            task = msg.content.split("Task:")[-1].split("\n")[0].strip()
            break

    prompt = AGENT_PROMPTS[agent_name].format(
        task=task,
        agent_instructions=_get_agent_instructions(agent_config),
    )
    messages = [SystemMessage(content=prompt), *state["messages"]]

    response = await llm_with_tools.ainvoke(messages)
    result_messages: list[Any] = [response]

    # Execute any tool calls (respects HITL config)
    while hasattr(response, "tool_calls") and response.tool_calls:
        tool_result = await handle_tools(
            {**state, "messages": [*state["messages"], *result_messages]},
            config,
        )
        result_messages.extend(tool_result["messages"])
        response = await llm_with_tools.ainvoke(
            [SystemMessage(content=prompt), *state["messages"], *result_messages]
        )
        result_messages.append(response)

    agent_output = response.content or f"{agent_name} completed."
    agent_outputs = {**(state.get("agent_outputs") or {}), agent_name: agent_output}

    return {
        "agent_outputs": agent_outputs,
        "messages": result_messages,
    }


async def researcher_node(state: SupervisorState, config: RunnableConfig) -> dict:
    return await _run_sub_agent(state, config, "researcher")


async def coder_node(state: SupervisorState, config: RunnableConfig) -> dict:
    return await _run_sub_agent(state, config, "coder")


async def reviewer_node(state: SupervisorState, config: RunnableConfig) -> dict:
    return await _run_sub_agent(state, config, "reviewer")


# --------------- Graph routing ---------------


def route_delegation(state: SupervisorState) -> str:
    """Route after delegation approval."""
    next_agent = state.get("next_agent", "done")
    if next_agent in AVAILABLE_AGENTS:
        return next_agent
    return END


# --------------- Graph builder ---------------


def build_multi_agent_graph() -> StateGraph:
    graph = StateGraph(SupervisorState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("approve_delegation", delegation_approval_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("coder", coder_node)
    graph.add_node("reviewer", reviewer_node)

    graph.add_conditional_edges(START, make_entry_router("supervisor"), ["supervisor", END])
    graph.add_edge("supervisor", "approve_delegation")
    graph.add_conditional_edges(
        "approve_delegation",
        route_delegation,
        ["researcher", "coder", "reviewer", END],
    )
    graph.add_edge("researcher", "supervisor")
    graph.add_edge("coder", "supervisor")
    graph.add_edge("reviewer", "supervisor")

    return graph
