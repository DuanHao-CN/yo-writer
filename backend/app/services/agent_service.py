import uuid

from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import APIError
from app.models.agent import Agent, AgentVersion
from app.schemas.agent import AgentCreate, AgentUpdate


async def create_agent(
    db: AsyncSession, workspace_id: str, data: AgentCreate
) -> Agent:
    slug = slugify(data.name)

    existing = await db.scalar(
        select(Agent).where(
            Agent.workspace_id == uuid.UUID(workspace_id),
            Agent.slug == slug,
        )
    )
    if existing:
        raise APIError(
            code="AGENT_SLUG_CONFLICT",
            message=f"Agent with slug '{slug}' already exists in this workspace",
            status_code=409,
        )

    agent = Agent(
        workspace_id=uuid.UUID(workspace_id),
        name=data.name,
        slug=slug,
        description=data.description,
        icon=data.icon,
        config=data.config.model_dump(),
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


async def list_agents(
    db: AsyncSession, workspace_id: str, offset: int = 0, limit: int = 20
) -> tuple[list[Agent], int]:
    wid = uuid.UUID(workspace_id)

    total = await db.scalar(
        select(func.count()).select_from(Agent).where(Agent.workspace_id == wid)
    )

    result = await db.execute(
        select(Agent)
        .where(Agent.workspace_id == wid)
        .order_by(Agent.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), total or 0


async def list_all_agents(db: AsyncSession, workspace_id: str) -> list[Agent]:
    """Return all agents for runtime/bootstrap flows that cannot paginate."""
    wid = uuid.UUID(workspace_id)
    result = await db.execute(
        select(Agent)
        .where(Agent.workspace_id == wid)
        .order_by(Agent.created_at.desc())
    )
    return list(result.scalars().all())


async def get_agent(db: AsyncSession, agent_id: uuid.UUID) -> Agent:
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise APIError(
            code="AGENT_NOT_FOUND",
            message="Agent not found",
            status_code=404,
        )
    return agent


async def update_agent(
    db: AsyncSession, agent_id: uuid.UUID, data: AgentUpdate
) -> Agent:
    agent = await get_agent(db, agent_id)

    update_data = data.model_dump(exclude_unset=True)
    changelog = update_data.pop("changelog", None)

    # Snapshot current config as a version before applying changes
    if "config" in update_data and update_data["config"] is not None:
        version = AgentVersion(
            agent_id=agent.id,
            version=agent.current_version,
            config=agent.config,
            changelog=changelog,
        )
        db.add(version)
        update_data["config"] = data.config.model_dump()
        update_data["current_version"] = agent.current_version + 1

    for field, value in update_data.items():
        setattr(agent, field, value)

    await db.commit()
    await db.refresh(agent)
    return agent


async def delete_agent(db: AsyncSession, agent_id: uuid.UUID) -> str:
    """Delete agent and return its slug for runtime cleanup."""
    agent = await get_agent(db, agent_id)
    slug = agent.slug
    await db.delete(agent)
    await db.commit()
    return slug


async def list_versions(
    db: AsyncSession, agent_id: uuid.UUID, offset: int = 0, limit: int = 20
) -> tuple[list[AgentVersion], int]:
    """List version history for an agent."""
    await get_agent(db, agent_id)

    total = await db.scalar(
        select(func.count())
        .select_from(AgentVersion)
        .where(AgentVersion.agent_id == agent_id)
    )

    result = await db.execute(
        select(AgentVersion)
        .where(AgentVersion.agent_id == agent_id)
        .order_by(AgentVersion.version.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), total or 0


async def get_version(
    db: AsyncSession, agent_id: uuid.UUID, version: int
) -> AgentVersion:
    """Get a specific version of an agent."""
    await get_agent(db, agent_id)

    result = await db.scalar(
        select(AgentVersion).where(
            AgentVersion.agent_id == agent_id,
            AgentVersion.version == version,
        )
    )
    if not result:
        raise APIError(
            code="VERSION_NOT_FOUND",
            message=f"Version {version} not found for this agent",
            status_code=404,
        )
    return result


async def rollback_agent(
    db: AsyncSession, agent_id: uuid.UUID, target_version: int
) -> Agent:
    """Rollback agent config to a previous version."""
    target = await get_version(db, agent_id, target_version)
    agent = await get_agent(db, agent_id)

    # Snapshot current config before rollback
    version = AgentVersion(
        agent_id=agent.id,
        version=agent.current_version,
        config=agent.config,
        changelog=f"Rollback to version {target_version}",
    )
    db.add(version)

    agent.config = target.config
    agent.current_version = agent.current_version + 1

    await db.commit()
    await db.refresh(agent)
    return agent


async def list_runs(
    db: AsyncSession, agent_id: uuid.UUID
) -> list:
    from app.models.agent import AgentRun

    # Verify agent exists
    await get_agent(db, agent_id)

    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.agent_id == agent_id)
        .order_by(AgentRun.started_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())
