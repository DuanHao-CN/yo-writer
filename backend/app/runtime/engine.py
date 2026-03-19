"""AgentRuntime — compiles and runs LangGraph agent graphs.

Manages compiled graph instances and routes run requests.
"""

import time
import uuid
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.core.database import async_session
from app.models.agent import Agent, AgentRun
from app.runtime.checkpointer import get_checkpointer, get_persistent_checkpointer
from app.runtime.graphs.multi_agent import build_multi_agent_graph
from app.runtime.graphs.plan_execute import build_plan_execute_graph
from app.runtime.graphs.react import build_react_graph
from app.runtime.graphs.react_hitl import build_react_hitl_graph


def _select_graph(config: dict) -> StateGraph:
    """Choose graph builder based on agent config."""
    graph_type = (config.get("graph") or {}).get("type", "react")

    if graph_type == "plan-execute":
        return build_plan_execute_graph()
    if graph_type == "multi-agent":
        return build_multi_agent_graph()

    # Default: react with optional HITL
    hitl = config.get("hitl") or {}
    if hitl.get("require_approval") or hitl.get("require_review"):
        return build_react_hitl_graph()
    return build_react_graph()


def _to_langchain_message(message: dict[str, Any]) -> BaseMessage:
    role = message.get("role")
    content = message.get("content", "")

    if role == "user":
        return HumanMessage(content=content)
    if role == "system":
        return SystemMessage(content=content)
    if role == "assistant":
        return AIMessage(content=content)
    if role == "tool":
        tool_call_id = message.get("tool_call_id")
        if not tool_call_id:
            raise ValueError("Tool messages require tool_call_id")
        return ToolMessage(content=content, tool_call_id=tool_call_id)

    raise ValueError(f"Unsupported message role: {role}")


def _serialize_message(message: BaseMessage) -> dict[str, Any]:
    role_map = {
        "human": "user",
        "system": "system",
        "ai": "assistant",
        "tool": "tool",
    }
    return {
        "role": role_map.get(getattr(message, "type", ""), "unknown"),
        "content": getattr(message, "content", ""),
    }


class AgentRuntime:
    def __init__(self) -> None:
        self.graphs: dict[str, CompiledStateGraph] = {}
        self.langgraph_configs: dict[str, dict[str, Any]] = {}

    def register_agent(self, slug: str, config: dict) -> None:
        """Build and compile a graph for the given agent, cache by slug."""
        checkpointer = get_persistent_checkpointer()
        graph = _select_graph(config)
        compiled = graph.compile(checkpointer=checkpointer)
        self.graphs[slug] = compiled
        self.langgraph_configs[slug] = {
            "configurable": {"agent_config": deepcopy(config)}
        }

    def unregister_agent(self, slug: str) -> None:
        """Remove an agent from the in-memory runtime registry."""
        self.graphs.pop(slug, None)
        self.langgraph_configs.pop(slug, None)

    def clear_registered_agents(self) -> None:
        """Reset the in-memory runtime registry."""
        self.graphs.clear()
        self.langgraph_configs.clear()

    def list_registered_agent_slugs(self) -> list[str]:
        """Return all registered agent slugs."""
        return list(self.graphs)

    def get_graph(self, slug: str) -> CompiledStateGraph | None:
        """Return the compiled graph for a registered agent."""
        return self.graphs.get(slug)

    def get_langgraph_config(self, slug: str) -> dict[str, Any] | None:
        """Return a defensive copy of the stored LangGraph config."""
        config = self.langgraph_configs.get(slug)
        if config is None:
            return None
        return deepcopy(config)

    async def run(
        self,
        agent: Agent,
        messages: list[dict],
        thread_id: str | None = None,
        conversation_id: uuid.UUID | None = None,
    ) -> dict:
        """Execute the agent graph with given messages.

        Returns the final message content and run metadata.
        Uses cached graph when available, falls back to per-request compilation.
        """
        thread_id = thread_id or str(uuid.uuid4())

        lc_messages = [_to_langchain_message(message) for message in messages]

        config = {
            "configurable": {
                "thread_id": thread_id,
                "agent_config": agent.config,
            }
        }

        run_id = uuid.uuid4()
        start_time = time.time()

        try:
            # Use cached graph if available, otherwise compile per-request
            if agent.slug in self.graphs:
                compiled = self.graphs[agent.slug]
                result = await compiled.ainvoke({"messages": lc_messages}, config)
            else:
                async with get_checkpointer() as checkpointer:
                    graph = _select_graph(agent.config)
                    compiled = graph.compile(checkpointer=checkpointer)
                    result = await compiled.ainvoke({"messages": lc_messages}, config)

            duration_ms = int((time.time() - start_time) * 1000)

            await self._save_run(
                run_id=run_id,
                agent_id=agent.id,
                conversation_id=conversation_id,
                agent_version=agent.current_version,
                status="completed",
                duration_ms=duration_ms,
            )

            return {
                "run_id": str(run_id),
                "thread_id": thread_id,
                "status": "completed",
                "duration_ms": duration_ms,
                "messages": [
                    _serialize_message(message) for message in result["messages"]
                ],
            }

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            await self._save_run(
                run_id=run_id,
                agent_id=agent.id,
                conversation_id=conversation_id,
                agent_version=agent.current_version,
                status="failed",
                duration_ms=duration_ms,
                error=str(e),
            )
            raise

    async def _save_run(
        self,
        run_id: uuid.UUID,
        agent_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
        agent_version: int,
        status: str,
        duration_ms: int,
        error: str | None = None,
    ) -> None:
        async with async_session() as db:
            run = AgentRun(
                id=run_id,
                agent_id=agent_id,
                conversation_id=conversation_id,
                agent_version=agent_version,
                status=status,
                duration_ms=duration_ms,
                error=error,
            )
            if status == "completed":
                run.completed_at = datetime.now(UTC)
            db.add(run)
            await db.commit()


# Singleton
agent_runtime = AgentRuntime()
