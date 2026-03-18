import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agui import register_copilotkit_endpoint
from app.api.v1 import agents, conversations
from app.core.config import settings
from app.core.constants import DEV_WORKSPACE_ID
from app.core.database import async_session
from app.core.errors import register_error_handlers
from app.runtime.checkpointer import close_checkpointer, init_checkpointer
from app.runtime.engine import agent_runtime
from app.services import agent_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_checkpointer()

    async with async_session() as db:
        db_agents, _ = await agent_service.list_agents(db, DEV_WORKSPACE_ID)
        for agent in db_agents:
            agent_runtime.register_agent(agent.slug, agent.config)
        logger.info("Loaded %d agent(s) into runtime", len(db_agents))

    register_copilotkit_endpoint(app, agent_runtime.graphs)

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


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.VERSION}
