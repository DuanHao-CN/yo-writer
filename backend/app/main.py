import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agui import register_copilotkit_endpoint
from app.api.v1 import agents, conversations, sandbox, tools
from app.core.config import settings
from app.core.constants import DEV_WORKSPACE_ID
from app.core.database import async_session
from app.core.errors import register_error_handlers
from app.runtime.checkpointer import close_checkpointer, init_checkpointer
from app.runtime.engine import agent_runtime
from app.services import agent_service
from app.services.tool_service import seed_builtin_tools

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_checkpointer()
    agent_runtime.clear_registered_agents()

    async with async_session() as db:
        db_agents = await agent_service.list_all_agents(db, DEV_WORKSPACE_ID)
        for agent in db_agents:
            agent_runtime.register_agent(agent.slug, agent.config)
        logger.info("Loaded %d agent(s) into runtime", len(db_agents))

        await seed_builtin_tools(db, DEV_WORKSPACE_ID)
        logger.info("Seeded builtin tools")

    register_copilotkit_endpoint(app, agent_runtime)

    yield

    # Shutdown
    await close_checkpointer()


app = FastAPI(
    title="YoAgent API",
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(agents.router)
app.include_router(conversations.router)
app.include_router(tools.router)
app.include_router(sandbox.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.VERSION}
