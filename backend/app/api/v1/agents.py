import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEV_WORKSPACE_ID
from app.core.database import get_db
from app.runtime.engine import agent_runtime
from app.schemas.agent import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
    AgentVersionListResponse,
    AgentVersionResponse,
)
from app.schemas.conversation import AgentRunResponse, RunAgentRequest
from app.schemas.tool import AgentToolBind, AgentToolResponse
from app.services import agent_service, tool_service

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.post("/", response_model=AgentResponse, status_code=201)
async def create_agent(
    data: AgentCreate, db: AsyncSession = Depends(get_db)
) -> AgentResponse:
    agent = await agent_service.create_agent(db, DEV_WORKSPACE_ID, data)
    agent_runtime.register_agent(agent.slug, agent.config)
    return AgentResponse.model_validate(agent)


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> AgentListResponse:
    items, total = await agent_service.list_agents(db, DEV_WORKSPACE_ID, offset, limit)
    return AgentListResponse(
        items=[AgentResponse.model_validate(a) for a in items],
        total=total,
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> AgentResponse:
    agent = await agent_service.get_agent(db, agent_id)
    return AgentResponse.model_validate(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: uuid.UUID,
    data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    old_slug = (await agent_service.get_agent(db, agent_id)).slug
    agent = await agent_service.update_agent(db, agent_id, data)
    if old_slug != agent.slug:
        agent_runtime.unregister_agent(old_slug)
    agent_runtime.register_agent(agent.slug, agent.config)
    return AgentResponse.model_validate(agent)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> None:
    slug = await agent_service.delete_agent(db, agent_id)
    agent_runtime.unregister_agent(slug)


@router.post("/{agent_id}/run")
async def run_agent(
    agent_id: uuid.UUID,
    data: RunAgentRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    agent = await agent_service.get_agent(db, agent_id)
    result = await agent_runtime.run(
        agent=agent,
        messages=[{"role": m.role, "content": m.content} for m in data.messages],
    )
    return result


@router.get("/{agent_id}/runs", response_model=list[AgentRunResponse])
async def list_agent_runs(
    agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> list[AgentRunResponse]:
    runs = await agent_service.list_runs(db, agent_id)
    return [AgentRunResponse.model_validate(r) for r in runs]


# --------------- Agent Versioning ---------------


@router.get("/{agent_id}/versions", response_model=AgentVersionListResponse)
async def list_agent_versions(
    agent_id: uuid.UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> AgentVersionListResponse:
    items, total = await agent_service.list_versions(db, agent_id, offset, limit)
    return AgentVersionListResponse(
        items=[AgentVersionResponse.model_validate(v) for v in items],
        total=total,
    )


@router.get("/{agent_id}/versions/{version}", response_model=AgentVersionResponse)
async def get_agent_version(
    agent_id: uuid.UUID,
    version: int,
    db: AsyncSession = Depends(get_db),
) -> AgentVersionResponse:
    v = await agent_service.get_version(db, agent_id, version)
    return AgentVersionResponse.model_validate(v)


@router.post("/{agent_id}/rollback/{version}", response_model=AgentResponse)
async def rollback_agent(
    agent_id: uuid.UUID,
    version: int,
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    agent = await agent_service.rollback_agent(db, agent_id, version)
    agent_runtime.register_agent(agent.slug, agent.config)
    return AgentResponse.model_validate(agent)


# --------------- Agent-Tool Binding ---------------


@router.post("/{agent_id}/tools", response_model=AgentToolResponse, status_code=201)
async def bind_tool(
    agent_id: uuid.UUID,
    data: AgentToolBind,
    db: AsyncSession = Depends(get_db),
) -> AgentToolResponse:
    await agent_service.get_agent(db, agent_id)
    agent_tool = await tool_service.bind_tool(
        db, agent_id, data.tool_id, data.config_override
    )
    return AgentToolResponse.model_validate(agent_tool)


@router.get("/{agent_id}/tools", response_model=list[AgentToolResponse])
async def list_agent_tools(
    agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> list[AgentToolResponse]:
    await agent_service.get_agent(db, agent_id)
    items = await tool_service.list_agent_tools(db, agent_id)
    return [AgentToolResponse.model_validate(at) for at in items]


@router.delete("/{agent_id}/tools/{tool_id}", status_code=204)
async def unbind_tool(
    agent_id: uuid.UUID,
    tool_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    await tool_service.unbind_tool(db, agent_id, tool_id)
