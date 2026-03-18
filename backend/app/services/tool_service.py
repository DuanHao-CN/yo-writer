import time
import uuid

from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import APIError
from app.models.tool import AgentTool, Tool
from app.runtime.mcp_gateway import call_mcp_tool
from app.schemas.tool import ToolCreate, ToolUpdate


async def create_tool(
    db: AsyncSession, workspace_id: str, data: ToolCreate
) -> Tool:
    slug = slugify(data.name)

    existing = await db.scalar(
        select(Tool).where(
            Tool.workspace_id == uuid.UUID(workspace_id),
            Tool.slug == slug,
        )
    )
    if existing:
        raise APIError(
            code="TOOL_SLUG_CONFLICT",
            message=f"Tool with slug '{slug}' already exists in this workspace",
            status_code=409,
        )

    tool = Tool(
        workspace_id=uuid.UUID(workspace_id),
        name=data.name,
        slug=slug,
        description=data.description,
        type=data.type,
        mcp_uri=data.mcp_uri,
        config=data.config,
        schema_json=data.schema_json,
    )
    db.add(tool)
    await db.commit()
    await db.refresh(tool)
    return tool


async def list_tools(
    db: AsyncSession, workspace_id: str, offset: int = 0, limit: int = 20
) -> tuple[list[Tool], int]:
    wid = uuid.UUID(workspace_id)

    total = await db.scalar(
        select(func.count()).select_from(Tool).where(Tool.workspace_id == wid)
    )

    result = await db.execute(
        select(Tool)
        .where(Tool.workspace_id == wid)
        .order_by(Tool.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), total or 0


async def get_tool(db: AsyncSession, tool_id: uuid.UUID) -> Tool:
    tool = await db.get(Tool, tool_id)
    if not tool:
        raise APIError(
            code="TOOL_NOT_FOUND",
            message="Tool not found",
            status_code=404,
        )
    return tool


async def update_tool(
    db: AsyncSession, tool_id: uuid.UUID, data: ToolUpdate
) -> Tool:
    tool = await get_tool(db, tool_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tool, field, value)

    await db.commit()
    await db.refresh(tool)
    return tool


async def delete_tool(db: AsyncSession, tool_id: uuid.UUID) -> None:
    tool = await get_tool(db, tool_id)
    await db.delete(tool)
    await db.commit()


async def test_tool(tool_name: str, arguments: dict) -> dict:
    """Directly call a gateway tool and return result + timing."""
    start = time.time()
    try:
        result = await call_mcp_tool(tool_name, arguments)
        duration_ms = int((time.time() - start) * 1000)
        return {"result": result, "duration_ms": duration_ms, "status": "success"}
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        return {"result": str(exc), "duration_ms": duration_ms, "status": "error"}


async def bind_tool(
    db: AsyncSession,
    agent_id: uuid.UUID,
    tool_id: uuid.UUID,
    config_override: dict | None = None,
) -> AgentTool:
    # Verify tool exists
    await get_tool(db, tool_id)

    existing = await db.get(AgentTool, (agent_id, tool_id))
    if existing:
        raise APIError(
            code="TOOL_ALREADY_BOUND",
            message="Tool is already bound to this agent",
            status_code=409,
        )

    agent_tool = AgentTool(
        agent_id=agent_id,
        tool_id=tool_id,
        config_override=config_override or {},
    )
    db.add(agent_tool)
    await db.commit()
    await db.refresh(agent_tool)
    return agent_tool


async def unbind_tool(
    db: AsyncSession, agent_id: uuid.UUID, tool_id: uuid.UUID
) -> None:
    agent_tool = await db.get(AgentTool, (agent_id, tool_id))
    if not agent_tool:
        raise APIError(
            code="TOOL_BINDING_NOT_FOUND",
            message="Tool is not bound to this agent",
            status_code=404,
        )
    await db.delete(agent_tool)
    await db.commit()


async def list_agent_tools(
    db: AsyncSession, agent_id: uuid.UUID
) -> list[AgentTool]:
    result = await db.execute(
        select(AgentTool).where(AgentTool.agent_id == agent_id)
    )
    return list(result.scalars().all())


async def seed_builtin_tools(db: AsyncSession, workspace_id: str) -> None:
    """Upsert builtin tools (web-search, file-ops, code-sandbox) for the workspace."""
    wid = uuid.UUID(workspace_id)
    builtins = [
        {
            "name": "Web Search",
            "slug": "web-search",
            "description": "Search the web for information",
            "type": "builtin",
            "mcp_uri": "builtin://web-search",
            "schema_json": {
                "tools": ["builtin_web-search_web_search"],
            },
        },
        {
            "name": "File Operations",
            "slug": "file-ops",
            "description": "Read and write files",
            "type": "builtin",
            "mcp_uri": "builtin://file-ops",
            "schema_json": {
                "tools": [
                    "builtin_file-ops_read_file",
                    "builtin_file-ops_write_file",
                ],
            },
        },
        {
            "name": "Code Sandbox",
            "slug": "code-sandbox",
            "description": "Execute Python code in a secure sandbox",
            "type": "builtin",
            "mcp_uri": "builtin://code-sandbox",
            "schema_json": {
                "tools": ["builtin_code-sandbox_code_sandbox"],
            },
        },
    ]

    for spec in builtins:
        existing = await db.scalar(
            select(Tool).where(Tool.workspace_id == wid, Tool.slug == spec["slug"])
        )
        if existing:
            continue

        tool = Tool(workspace_id=wid, **spec)
        db.add(tool)

    await db.commit()
