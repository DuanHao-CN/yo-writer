"""CopilotKit / AG-UI single-endpoint for streaming chat.

Implements the CopilotKit "single endpoint" protocol directly.
The frontend (<CopilotKit useSingleEndpoint>) sends all requests as
POST /copilotkit with {"method": "...", "params": {...}, "body": {...}}.

This bypasses CopilotKitRemoteEndpoint which has compatibility issues
with LangGraphAGUIAgent (missing execute/dict_repr on base class).
"""

import logging
from copy import deepcopy
from typing import Any

from ag_ui.core.types import RunAgentInput
from ag_ui.encoder import EventEncoder
from copilotkit import LangGraphAGUIAgent
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

logger = logging.getLogger(__name__)


def register_copilotkit_endpoint(
    app: FastAPI,
    runtime: Any,
) -> None:
    """Register the CopilotKit single endpoint.

    `runtime` is an AgentRuntime instance (duck-typed to avoid circular import).
    Required attrs: graphs, langgraph_configs.
    """

    def _parse_envelope(body: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Parse CopilotKit single-endpoint envelope.

        Merges envelope params (routing info like agentId) with body (run payload
        like messages, threadId). Body wins on key conflicts.
        """
        method = body.get("method", "")
        params = body.get("params") or {}
        payload = body.get("body") or {}
        return method, {**params, **payload}

    def _info() -> JSONResponse:
        return JSONResponse(
            content={
                "agents": {
                    slug: {"description": f"Agent: {slug}"}
                    for slug in runtime.graphs
                },
                "version": "1.0.0",
            }
        )

    def _agent_run(
        params: dict[str, Any], request: Request, method: str,
    ) -> StreamingResponse:
        agent_slug = params.get("agentId", "")
        graph = runtime.graphs.get(agent_slug)
        if graph is None:
            raise HTTPException(404, detail=f"Agent not found: {agent_slug}")

        config = deepcopy(runtime.langgraph_configs.get(agent_slug))
        agent = LangGraphAGUIAgent(
            name=agent_slug,
            description=f"Agent: {agent_slug}",
            graph=graph,
            config=config,
        )

        # Provide defaults for required RunAgentInput fields.
        run_params: dict[str, Any] = {
            "threadId": params.get("threadId", ""),
            "runId": params.get("runId", ""),
            "state": params.get("state", {}),
            "messages": params.get("messages", []),
            "tools": params.get("tools", []),
            "context": params.get("context", []),
            "forwardedProps": params.get("forwardedProps", {}),
            **{k: v for k, v in params.items() if k not in (
                "threadId", "runId", "state", "messages",
                "tools", "context", "forwardedProps", "agentId",
            )},
        }
        try:
            run_input = RunAgentInput(**run_params)
        except Exception as exc:
            raise HTTPException(422, detail=str(exc)) from exc

        accept_header = request.headers.get("accept", "")
        encoder = EventEncoder(accept=accept_header)

        async def event_generator():
            try:
                logger.info(
                    "CopilotKit %s agent=%s thread=%s messages=%d",
                    method, agent_slug,
                    run_params["threadId"], len(run_params["messages"]),
                )
                async for event in agent.run(run_input):
                    event_type = getattr(event, "type", "?")
                    step = getattr(event, "step_name", None)
                    extra = f" step={step}" if step else ""
                    logger.info("AG-UI event: %s%s", event_type, extra)
                    yield encoder.encode(event)
            except Exception:
                logger.exception(
                    "CopilotKit stream failed for agent=%s thread=%s",
                    agent_slug, run_params["threadId"],
                )
                raise

        return StreamingResponse(
            event_generator(),
            media_type=encoder.get_content_type(),
        )

    @app.post("/copilotkit")
    async def copilotkit_endpoint(request: Request) -> Any:
        body = await request.json()
        method, params = _parse_envelope(body)

        if method == "info":
            return _info()
        if method in ("agent/run", "agent/connect"):
            return _agent_run(params, request, method)
        if method == "agent/stop":
            return JSONResponse(content={"ok": True})

        raise HTTPException(404, detail=f"Unknown method: {method}")

    @app.get("/copilotkit/info")
    async def copilotkit_info() -> Any:
        """REST-style info endpoint (used when transport=rest)."""
        return _info()

    logger.info(
        "CopilotKit endpoint registered with %d agent(s): %s",
        len(runtime.graphs), list(runtime.graphs),
    )
