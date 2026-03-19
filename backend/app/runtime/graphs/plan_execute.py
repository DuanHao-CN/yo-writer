"""Plan-Execute agent graph.

Structure:
    START -> entry_router -> planner -> approve_plan -> executor (loop) -> synthesizer -> END

Design notes:
    - Planner generates a step-by-step plan as a JSON list.
    - Plan approval uses HITL interrupt so the user can approve/edit/reject.
    - Executor runs each step with LLM + bound tools (MCP gateway).
    - Synthesizer combines all step results into a final answer.
"""

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
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


class PlanExecuteState(AgentState):
    """Extended state for plan-execute graphs."""

    plan: list[str]
    current_step: int
    step_results: list[str]
    final_answer: str


PLANNER_PROMPT = """You are a planning assistant. Given the user's request, create a step-by-step plan to accomplish it.

{agent_instructions}

Return your plan as a JSON object with a single key "steps" containing an array of step descriptions.
Each step should be a concise, actionable instruction.

Example:
{{"steps": ["Research the topic using available tools", "Analyze the findings", "Write a summary"]}}

Only return the JSON object, nothing else."""

EXECUTOR_PROMPT = """You are executing step {step_num} of a plan.

{agent_instructions}

Overall plan:
{plan}

Current step: {current_step}

Previous step results:
{previous_results}

Execute this step using the available tools. Provide a clear result."""

SYNTHESIZER_PROMPT = """You executed a multi-step plan. Synthesize all results into a clear, comprehensive final answer.

{agent_instructions}

Plan:
{plan}

Step results:
{step_results}

Provide the final answer to the user's original request."""


# --------------- Graph nodes ---------------


def _get_agent_instructions(agent_config: dict) -> str:
    """Extract system prompt as additional instructions for advanced graph nodes."""
    prompt = agent_config.get("system_prompt", "")
    if prompt and prompt != "You are a helpful assistant.":
        return f"Additional instructions from agent configuration:\n{prompt}"
    return ""


async def planner_node(state: PlanExecuteState, config: RunnableConfig) -> dict:
    """Generate a step-by-step plan from the user's request."""
    agent_config = config.get("configurable", {}).get("agent_config", {})
    llm = _build_llm(agent_config)

    messages = [
        SystemMessage(content=PLANNER_PROMPT.format(
            agent_instructions=_get_agent_instructions(agent_config),
        )),
        *state["messages"],
    ]

    response = await llm.ainvoke(messages)
    content = response.content

    # Parse the plan from JSON response
    try:
        parsed = json.loads(content)
        steps = parsed.get("steps", [])
    except (json.JSONDecodeError, AttributeError):
        # Fallback: treat each line as a step
        steps = [line.strip() for line in content.strip().split("\n") if line.strip()]

    return {
        "plan": steps,
        "current_step": 0,
        "step_results": [],
        "messages": [AIMessage(content=f"Plan created with {len(steps)} steps:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps)))],
    }


async def plan_approval_node(state: PlanExecuteState) -> dict:
    """Interrupt for human approval of the plan."""
    resume_value = interrupt({
        "type": "plan_approval",
        "plan": state["plan"],
        "message": "Review the proposed plan before execution begins.",
    })

    if isinstance(resume_value, str):
        resume_value = json.loads(resume_value)

    action = resume_value.get("action", "reject")

    if action == "reject":
        return {
            "final_answer": "Plan was rejected by user.",
            "messages": [AIMessage(content="Plan was rejected.")],
        }

    if action == "edit":
        edited_plan = resume_value.get("edited_plan", state["plan"])
        return {
            "plan": edited_plan,
            "messages": [AIMessage(content=f"Plan updated with {len(edited_plan)} steps:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(edited_plan)))],
        }

    # approve
    return {}


def _select_tool_handler(agent_config: dict):
    """Return HITL-aware tool handler when approval/review lists are configured."""
    hitl = agent_config.get("hitl") or {}
    if hitl.get("require_approval") or hitl.get("require_review"):
        return tool_node_with_hitl
    return tool_node


async def executor_node(state: PlanExecuteState, config: RunnableConfig) -> dict:
    """Execute the current plan step with LLM + tools."""
    agent_config = config.get("configurable", {}).get("agent_config", {})
    llm = _build_llm(agent_config)
    bound_tools = await _get_bound_tools(state)
    llm_with_tools = llm.bind_tools(bound_tools)
    handle_tools = _select_tool_handler(agent_config)

    step_idx = state["current_step"]
    plan = state["plan"]
    current_step = plan[step_idx] if step_idx < len(plan) else "Complete the task."

    previous_results = "\n".join(
        f"Step {i+1}: {r}" for i, r in enumerate(state["step_results"])
    ) or "None yet."

    prompt = EXECUTOR_PROMPT.format(
        step_num=step_idx + 1,
        plan="\n".join(f"{i+1}. {s}" for i, s in enumerate(plan)),
        current_step=current_step,
        previous_results=previous_results,
        agent_instructions=_get_agent_instructions(agent_config),
    )

    messages = [
        SystemMessage(content=prompt),
        *state["messages"],
    ]

    # Run LLM — handle tool calls in a loop until we get a text response
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

    step_result = response.content or f"Step {step_idx + 1} completed."
    new_results = [*state["step_results"], step_result]

    return {
        "current_step": step_idx + 1,
        "step_results": new_results,
        "messages": result_messages,
    }


async def synthesizer_node(state: PlanExecuteState, config: RunnableConfig) -> dict:
    """Synthesize all step results into a final answer."""
    agent_config = config.get("configurable", {}).get("agent_config", {})
    llm = _build_llm(agent_config)

    step_results = "\n".join(
        f"Step {i+1}: {r}" for i, r in enumerate(state["step_results"])
    )

    prompt = SYNTHESIZER_PROMPT.format(
        plan="\n".join(f"{i+1}. {s}" for i, s in enumerate(state["plan"])),
        step_results=step_results,
        agent_instructions=_get_agent_instructions(agent_config),
    )

    messages = [SystemMessage(content=prompt), *state["messages"]]
    response = await llm.ainvoke(messages)

    return {
        "final_answer": response.content,
        "messages": [response],
    }


# --------------- Graph routing ---------------


def route_after_approval(state: PlanExecuteState) -> str:
    """Route after plan approval: execute if approved, end if rejected."""
    if state.get("final_answer"):
        return END
    return "execute"


def route_after_execute(state: PlanExecuteState) -> str:
    """Route after step execution: more steps -> execute, done -> synthesize."""
    if state["current_step"] >= len(state["plan"]):
        return "synthesize"
    return "execute"


# --------------- Graph builder ---------------


def build_plan_execute_graph() -> StateGraph:
    graph = StateGraph(PlanExecuteState)

    graph.add_node("plan", planner_node)
    graph.add_node("approve_plan", plan_approval_node)
    graph.add_node("execute", executor_node)
    graph.add_node("synthesize", synthesizer_node)

    graph.add_conditional_edges(START, make_entry_router("plan"), ["plan", END])
    graph.add_edge("plan", "approve_plan")
    graph.add_conditional_edges("approve_plan", route_after_approval, ["execute", END])
    graph.add_conditional_edges("execute", route_after_execute, ["execute", "synthesize"])
    graph.add_edge("synthesize", END)

    return graph
