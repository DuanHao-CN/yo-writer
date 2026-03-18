# Phase 02: Agent Core — Data Model & LangGraph ReAct

## Meta

| Field | Value |
|-------|-------|
| **Goal** | Agent CRUD API, conversation management, and a working ReAct LangGraph agent |
| **Prerequisites** | Phase 01 (scaffold, database, FastAPI) |
| **Effort** | 2-3 days |
| **Key Technologies** | LangGraph, SQLAlchemy, AsyncPostgresSaver, FastAPI |

---

## Context

This phase builds the core agent infrastructure: database tables for agents, conversations, messages, and runs; CRUD API endpoints; and a ReAct (Reasoning + Acting) agent graph using LangGraph. The ReAct graph uses a mock tool node for now (tools are Phase 04).

We use hardcoded dev constants (from Phase 01) — no authentication.

The agent runtime is structured so that `should_continue` and `tool_node` are separate importable functions. Phase 06 (HITL) will wrap these with interrupt logic.

---

## Data Models

### Alembic Migration

Create a new migration with these tables:

```sql
-- Agent
CREATE TABLE agents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL,  -- no FK yet, Phase 08 adds users/workspaces tables
    name            VARCHAR(100) NOT NULL,
    slug            VARCHAR(100) NOT NULL,
    description     TEXT,
    icon            VARCHAR(50),
    status          VARCHAR(20) DEFAULT 'draft',    -- draft | active | archived
    visibility      VARCHAR(20) DEFAULT 'private',  -- private | workspace | public
    current_version INT DEFAULT 1,
    config          JSONB NOT NULL,                  -- full agent configuration
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (workspace_id, slug)
);

-- Agent Versions
CREATE TABLE agent_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        UUID REFERENCES agents(id) ON DELETE CASCADE,
    version         INT NOT NULL,
    config          JSONB NOT NULL,
    changelog       TEXT,
    created_by      UUID,  -- no FK yet, Phase 08
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (agent_id, version)
);

-- Conversations
CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        UUID REFERENCES agents(id) ON DELETE CASCADE,
    user_id         UUID,  -- no FK yet, Phase 08
    title           VARCHAR(255),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Messages
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,  -- user | assistant | system | tool
    content         TEXT,
    tool_calls      JSONB,
    tool_call_id    VARCHAR(100),
    metadata        JSONB DEFAULT '{}',
    tokens_input    INT,
    tokens_output   INT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);

-- Agent Runs
CREATE TABLE agent_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    agent_id        UUID REFERENCES agents(id),
    agent_version   INT,
    status          VARCHAR(20) DEFAULT 'running',  -- running | completed | failed | cancelled
    trigger_message_id UUID REFERENCES messages(id),
    total_tokens    INT DEFAULT 0,
    total_cost_usd  DECIMAL(10,6) DEFAULT 0,
    duration_ms     INT,
    error           TEXT,
    trace_id        VARCHAR(64),
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);
```

---

## API Endpoints

### Agent CRUD

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/agents` | Create agent (workspace_id from dev constant) |
| GET | `/api/v1/agents` | List agents in dev workspace |
| GET | `/api/v1/agents/{agent_id}` | Get agent details |
| PATCH | `/api/v1/agents/{agent_id}` | Update agent |
| DELETE | `/api/v1/agents/{agent_id}` | Delete agent |

**Create Agent Request**:

```json
{
  "name": "Data Analyst",
  "description": "Analyze CSV data and generate insights",
  "config": {
    "model": {
      "provider": "openai",
      "model_id": "gpt-4o",
      "temperature": 0.7,
      "max_tokens": 4096
    },
    "system_prompt": "You are a data analyst assistant.",
    "graph": {
      "type": "react",
      "max_iterations": 10
    }
  }
}
```

**Response**: `201 Created` with full agent object including generated `id`, `slug`, timestamps.

### Conversation API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/conversations` | Create conversation for an agent |
| GET | `/api/v1/conversations` | List conversations |
| GET | `/api/v1/conversations/{conv_id}` | Get conversation with messages |
| DELETE | `/api/v1/conversations/{conv_id}` | Delete conversation |
| POST | `/api/v1/conversations/{conv_id}/messages` | Send message (triggers agent run) |
| GET | `/api/v1/conversations/{conv_id}/messages` | Get message history |

### Agent Run

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/agents/{agent_id}/run` | Run agent (synchronous, streamed response) |
| GET | `/api/v1/agents/{agent_id}/runs` | List agent runs |
| GET | `/api/v1/agents/{agent_id}/runs/{run_id}` | Get run details |

**Run Agent Request**:

```json
{
  "messages": [{"role": "user", "content": "What is 2+2?"}],
  "stream": true
}
```

---

## Implementation Steps

### Step 1: SQLAlchemy Models

**File**: `backend/app/models/__init__.py`
**File**: `backend/app/models/agent.py`

```python
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.core.database import Base
import uuid

class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False)
    description = Column(Text)
    icon = Column(String(50))
    status = Column(String(20), default="draft")
    visibility = Column(String(20), default="private")
    current_version = Column(Integer, default=1)
    config = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

Similarly create `AgentVersion`, `Conversation`, `Message`, `AgentRun` models.

### Step 2: Pydantic Schemas

**File**: `backend/app/schemas/agent.py`

Define `AgentCreate`, `AgentUpdate`, `AgentResponse`, `AgentListResponse` schemas.

**File**: `backend/app/schemas/conversation.py`

Define `ConversationCreate`, `MessageCreate`, `MessageResponse`, etc.

### Step 3: Agent Service

**File**: `backend/app/services/agent_service.py`

CRUD operations using SQLAlchemy async sessions. Auto-generate `slug` from `name` using `slugify`.

### Step 4: API Routes

**File**: `backend/app/api/v1/agents.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.constants import DEV_WORKSPACE_ID

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

@router.post("/", status_code=201)
async def create_agent(data: AgentCreate, db: AsyncSession = Depends(get_db)):
    return await agent_service.create(db, DEV_WORKSPACE_ID, data)

# ... GET, PATCH, DELETE endpoints
```

**File**: `backend/app/api/v1/conversations.py`

### Step 5: Register routers in main.py

**File**: `backend/app/main.py`

```python
from app.api.v1 import agents, conversations
app.include_router(agents.router)
app.include_router(conversations.router)
```

### Step 6: LangGraph ReAct Graph

**File**: `backend/app/runtime/__init__.py`
**File**: `backend/app/runtime/graphs/__init__.py`
**File**: `backend/app/runtime/graphs/react.py`

```python
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import SystemMessage, ToolMessage

async def llm_node(state: MessagesState):
    """Call LLM, may produce tool calls."""
    model = get_model_for_agent(state["agent_config"])
    model_with_tools = model.bind_tools(state.get("available_tools", []))
    system = SystemMessage(content=state["agent_config"]["system_prompt"])
    response = await model_with_tools.ainvoke([system, *state["messages"]])
    return {"messages": [response]}

async def tool_node(state: MessagesState):
    """Execute tool calls — mock implementation for Phase 02.
    Phase 04 replaces this with MCP gateway routing.
    Phase 06 wraps this with HITL interrupt logic.
    """
    results = []
    for tool_call in state["messages"][-1].tool_calls:
        results.append(ToolMessage(
            content=f"[Mock] Tool '{tool_call['name']}' called with {tool_call['args']}",
            tool_call_id=tool_call["id"]
        ))
    return {"messages": results}

def should_continue(state: MessagesState):
    """Route: if LLM made tool calls → tools node, else → END.
    Phase 06 will wrap this to add HITL interrupt before tool execution.
    """
    last = state["messages"][-1]
    if not last.tool_calls:
        return END
    return "tools"

def build_react_graph() -> StateGraph:
    graph = StateGraph(MessagesState)
    graph.add_node("llm", llm_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "llm")
    graph.add_conditional_edges("llm", should_continue, ["tools", END])
    graph.add_edge("tools", "llm")
    return graph
```

### Step 7: Checkpointer

**File**: `backend/app/runtime/checkpointer.py`

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.core.config import settings

async def get_checkpointer():
    return AsyncPostgresSaver.from_conn_string(
        conn_string=settings.DATABASE_URL.replace("+asyncpg", "")
    )
```

### Step 8: AgentRuntime

**File**: `backend/app/runtime/engine.py`

```python
from fastapi import FastAPI
from langgraph.graph import CompiledGraph
from app.runtime.graphs.react import build_react_graph
from app.runtime.checkpointer import get_checkpointer

class AgentRuntime:
    def __init__(self, app: FastAPI):
        self.app = app
        self.agents: dict[str, CompiledGraph] = {}

    async def register_agent(self, agent_config: dict) -> None:
        graph = build_react_graph()
        compiled = graph.compile(checkpointer=await get_checkpointer())
        self.agents[agent_config["slug"]] = compiled

    async def run(self, agent_slug: str, messages: list, thread_id: str) -> dict:
        compiled = self.agents[agent_slug]
        config = {"configurable": {"thread_id": thread_id}}
        result = await compiled.ainvoke({"messages": messages}, config)
        return result
```

### Step 9: Run endpoint

**File**: `backend/app/api/v1/agents.py` (add to existing router)

```python
@router.post("/{agent_id}/run")
async def run_agent(agent_id: UUID, data: RunAgentRequest, db: AsyncSession = Depends(get_db)):
    agent = await agent_service.get(db, agent_id)
    # Ensure agent is registered in runtime
    runtime = get_agent_runtime()
    result = await runtime.run(agent.slug, data.messages, thread_id=str(uuid.uuid4()))
    return result
```

---

## Integration Points

- **Phase 01**: Uses `Base` from `database.py`, `settings` from `config.py`, Docker Compose PostgreSQL
- Alembic migration depends on Phase 01's Alembic setup

---

## Verification Checklist

- [ ] `uv run alembic upgrade head` — creates 5 tables in PostgreSQL
- [ ] `POST /api/v1/agents` — creates agent, returns 201 with generated ID and slug
- [ ] `GET /api/v1/agents` — lists agents in dev workspace
- [ ] `GET /api/v1/agents/{id}` — returns agent details
- [ ] `PATCH /api/v1/agents/{id}` — updates agent config
- [ ] `DELETE /api/v1/agents/{id}` — deletes agent
- [ ] `POST /api/v1/agents/{id}/run` with `{"messages": [{"role": "user", "content": "Hello"}]}` — returns LLM response
- [ ] `POST /api/v1/conversations` — creates conversation
- [ ] `POST /api/v1/conversations/{id}/messages` — stores message and triggers agent run
- [ ] Agent run with tool call triggers mock tool node, returns tool response in final output
- [ ] Checkpointer persists state — same thread_id resumes conversation

---

## Forward-Looking Notes

- **Phase 03** will add AG-UI endpoint using `add_langgraph_fastapi_endpoint` and the compiled graph from this phase.
- **Phase 04** will replace `tool_node` mock with real MCP gateway routing.
- **Phase 06** will wrap `should_continue` and `tool_node` with HITL interrupt logic — keep these as standalone importable functions (not lambdas or inline).
- The `agent_versions` table is created now but versioning logic (snapshot on update, rollback) is implemented in Phase 07.
- `workspace_id` and `user_id` columns exist but have no FK constraints until Phase 08 adds users/workspaces tables.
