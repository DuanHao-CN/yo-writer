"""CopilotKit / AG-UI single-endpoint for streaming chat.

Implements the CopilotKit "single endpoint" protocol directly.
The frontend (<CopilotKit useSingleEndpoint>) sends all requests as
POST /copilotkit with {"method": "...", "params": {...}}.

This bypasses CopilotKitRemoteEndpoint which has compatibility issues
with LangGraphAGUIAgent (missing execute/dict_repr on base class).
"""

import logging
from typing import Any

from ag_ui.core.types import RunAgentInput
from ag_ui.encoder import EventEncoder
from copilotkit import LangGraphAGUIAgent
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from langgraph.graph.state import CompiledStateGraph

logger = logging.getLogger(__name__)

# Module-level registry populated at startup
_agents: dict[str, LangGraphAGUIAgent] = {}


def register_copilotkit_endpoint(
    app: FastAPI,
    graphs: dict[str, CompiledStateGraph],
) -> None:
    """Register the CopilotKit single endpoint with all compiled agent graphs."""
    for slug, graph in graphs.items():
        _agents[slug] = LangGraphAGUIAgent(
            name=slug,
            description=f"Agent: {slug}",
            graph=graph,
        )

    @app.post("/copilotkit")
    async def copilotkit_endpoint(request: Request) -> Any:
        body = await request.json()
        method = body.get("method", "")
        params = body.get("params", {})

        if method == "info":
            return _handle_info()

        if method == "agent/run":
            return _handle_agent_run(params, request)

        if method == "agent/connect":
            return _handle_agent_run(params, request)

        if method == "agent/stop":
            return JSONResponse(content={"ok": True})

        raise HTTPException(status_code=404, detail=f"Unknown method: {method}")

    @app.get("/copilotkit/info")
    async def copilotkit_info() -> Any:
        """REST-style info endpoint (used when transport=rest)."""
        return _handle_info()

    logger.info(
        "CopilotKit endpoint registered with %d agent(s): %s",
        len(_agents),
        list(_agents),
    )


def _handle_info() -> JSONResponse:
    """Return runtime info including available agents."""
    return JSONResponse(
        content={
            "agents": {
                name: {"description": agent.description or ""}
                for name, agent in _agents.items()
            },
            "version": "1.0.0",
        }
    )


def _handle_agent_run(params: dict, request: Request) -> StreamingResponse:
    """Run an agent via the AG-UI streaming protocol."""
    agent_id = params.get("agentId", "")
    agent = _agents.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    run_input = RunAgentInput(**{
        k: v
        for k, v in params.items()
        if k in RunAgentInput.model_fields
    })

    accept_header = request.headers.get("accept", "")
    encoder = EventEncoder(accept=accept_header)

    async def event_generator():
        async for event in agent.run(run_input):
            yield encoder.encode(event)

    return StreamingResponse(
        event_generator(),
        media_type=encoder.get_content_type(),
    )
