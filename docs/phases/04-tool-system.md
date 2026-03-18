# Phase 04: Tool System — FastMCP Gateway & Built-in Tools

## Meta

| Field | Value |
|-------|-------|
| **Goal** | FastMCP gateway with built-in tools, tool CRUD API, and real tool execution in agent graph |
| **Prerequisites** | Phase 02 (agent core, ReAct graph) |
| **Effort** | 2-3 days |
| **Key Technologies** | FastMCP, MCP Protocol, LangGraph tool routing |

---

## Context

This phase replaces Phase 02's mock `tool_node` with a real FastMCP-based tool gateway. The gateway acts as an orchestrator: it mounts built-in MCP servers (web_search, file_ops) and routes tool calls from the LangGraph agent through the MCP protocol (ADR-002).

Tools are registered in the database, bound to agents, and all tool call results are recorded for observability.

### Architecture

```
LangGraph ReAct Agent
    └── tool_node()
          └── MCP Gateway (FastMCP Orchestrator)
                ├── builtin/web-search     → Mock web search
                ├── builtin/file-ops       → File operations
                └── user/{workspace}/...   → (Phase 08+)
```

---

## Data Models

### Alembic Migration

```sql
-- Tool Registry
CREATE TABLE tools (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL,  -- no FK yet
    name            VARCHAR(100) NOT NULL,
    slug            VARCHAR(100) NOT NULL,
    description     TEXT,
    type            VARCHAR(20) NOT NULL,           -- builtin | custom | marketplace
    mcp_uri         TEXT NOT NULL,                   -- mcp://builtin/code-sandbox
    config          JSONB DEFAULT '{}',
    credentials     JSONB DEFAULT '{}',              -- encrypted credentials
    schema_json     JSONB,                           -- tool input/output schema
    status          VARCHAR(20) DEFAULT 'active',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (workspace_id, slug)
);

-- Agent-Tool Binding
CREATE TABLE agent_tools (
    agent_id        UUID REFERENCES agents(id) ON DELETE CASCADE,
    tool_id         UUID REFERENCES tools(id) ON DELETE CASCADE,
    config_override JSONB DEFAULT '{}',
    PRIMARY KEY (agent_id, tool_id)
);

-- Tool Call Records
CREATE TABLE tool_calls (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_run_id    UUID REFERENCES agent_runs(id) ON DELETE CASCADE,
    tool_name       VARCHAR(100) NOT NULL,
    mcp_uri         TEXT,
    input_args      JSONB,
    output          JSONB,
    status          VARCHAR(20) DEFAULT 'pending',   -- pending | success | error
    duration_ms     INT,
    error           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## API Endpoints

### Tool CRUD

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/tools` | Register a tool |
| GET | `/api/v1/tools` | List tools in dev workspace |
| GET | `/api/v1/tools/{tool_id}` | Get tool details |
| PATCH | `/api/v1/tools/{tool_id}` | Update tool |
| DELETE | `/api/v1/tools/{tool_id}` | Delete tool |
| POST | `/api/v1/tools/{tool_id}/test` | Test tool invocation |

### Agent-Tool Binding

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/agents/{agent_id}/tools` | Bind tool to agent |
| GET | `/api/v1/agents/{agent_id}/tools` | List agent's tools |
| DELETE | `/api/v1/agents/{agent_id}/tools/{tool_id}` | Unbind tool from agent |

**Register Tool Request**:

```json
{
  "name": "Web Search",
  "description": "Search the web for information",
  "type": "builtin",
  "mcp_uri": "mcp://builtin/web-search",
  "schema_json": {
    "input": {
      "type": "object",
      "properties": {
        "query": {"type": "string", "description": "Search query"}
      },
      "required": ["query"]
    }
  }
}
```

**Bind Tool Request**:

```json
{
  "tool_id": "uuid-of-tool",
  "config_override": {}
}
```

---

## Implementation Steps

### Step 1: SQLAlchemy Models

**File**: `backend/app/models/tool.py`

```python
class Tool(Base):
    __tablename__ = "tools"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False)
    description = Column(Text)
    type = Column(String(20), nullable=False)
    mcp_uri = Column(Text, nullable=False)
    config = Column(JSONB, default={})
    credentials = Column(JSONB, default={})
    schema_json = Column(JSONB)
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class AgentTool(Base):
    __tablename__ = "agent_tools"
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("tools.id", ondelete="CASCADE"), primary_key=True)
    config_override = Column(JSONB, default={})

class ToolCall(Base):
    __tablename__ = "tool_calls"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_run_id = Column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"))
    tool_name = Column(String(100), nullable=False)
    mcp_uri = Column(Text)
    input_args = Column(JSONB)
    output = Column(JSONB)
    status = Column(String(20), default="pending")
    duration_ms = Column(Integer)
    error = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### Step 2: FastMCP Gateway

**File**: `backend/app/runtime/mcp_gateway.py`

```python
from fastmcp import FastMCP

# Platform-level MCP orchestrator
gateway = FastMCP("YoAgent-MCP-Gateway")

# Built-in: web search (mock)
builtin_search = FastMCP("builtin-web-search")

@builtin_search.tool
def web_search(query: str) -> str:
    """Search the web for information.

    Args:
        query: The search query
    """
    return f"[Mock search results for: {query}] — Replace with real search API in production."

# Built-in: file operations (mock)
builtin_files = FastMCP("builtin-file-ops")

@builtin_files.tool
def read_file(path: str) -> str:
    """Read a file from the workspace.

    Args:
        path: File path relative to workspace root
    """
    return f"[Mock file content for: {path}]"

@builtin_files.tool
def write_file(path: str, content: str) -> str:
    """Write content to a file in the workspace.

    Args:
        path: File path relative to workspace root
        content: File content to write
    """
    return f"[Mock] Wrote {len(content)} chars to {path}"

# Mount built-in servers
gateway.mount(builtin_search, namespace="builtin/web-search")
gateway.mount(builtin_files, namespace="builtin/file-ops")
```

### Step 3: Update ReAct Graph tool_node

**File**: `backend/app/runtime/graphs/react.py` (modify `tool_node`)

```python
from app.runtime.mcp_gateway import gateway

async def tool_node(state: MessagesState):
    """Execute tool calls through MCP Gateway.
    Each tool call is routed through the FastMCP orchestrator.
    """
    results = []
    for tool_call in state["messages"][-1].tool_calls:
        try:
            result = await gateway.call_tool(
                tool_name=tool_call["name"],
                arguments=tool_call["args"],
            )
            results.append(ToolMessage(
                content=str(result),
                tool_call_id=tool_call["id"]
            ))
        except Exception as e:
            results.append(ToolMessage(
                content=f"Error: {str(e)}",
                tool_call_id=tool_call["id"]
            ))
    return {"messages": results}
```

### Step 4: Bind tools to LLM

Update `llm_node` in `react.py` to bind the agent's available MCP tools to the LLM:

```python
async def llm_node(state: MessagesState):
    model = get_model_for_agent(state["agent_config"])
    # Get available tools from MCP gateway for this agent
    available_tools = await get_agent_mcp_tools(state["agent_config"])
    model_with_tools = model.bind_tools(available_tools)
    system = SystemMessage(content=state["agent_config"]["system_prompt"])
    response = await model_with_tools.ainvoke([system, *state["messages"]])
    return {"messages": [response]}
```

### Step 5: Tool Service & API Routes

**File**: `backend/app/services/tool_service.py`
**File**: `backend/app/api/v1/tools.py`

CRUD for tools + agent-tool binding endpoints.

### Step 6: Tool Call Recording

Add tool call recording to the `tool_node` — write each call to the `tool_calls` table with timing and status.

### Step 7: Seed Built-in Tools

On startup, ensure built-in tools exist in the database:

```python
# backend/app/services/tool_service.py
BUILTIN_TOOLS = [
    {"name": "Web Search", "slug": "web-search", "type": "builtin",
     "mcp_uri": "mcp://builtin/web-search", "description": "Search the web"},
    {"name": "File Operations", "slug": "file-ops", "type": "builtin",
     "mcp_uri": "mcp://builtin/file-ops", "description": "Read and write files"},
]

async def seed_builtin_tools(db: AsyncSession, workspace_id: UUID):
    for tool_data in BUILTIN_TOOLS:
        existing = await get_by_slug(db, workspace_id, tool_data["slug"])
        if not existing:
            await create(db, workspace_id, ToolCreate(**tool_data))
```

---

## Integration Points

- **Phase 02**: Replaces mock `tool_node` with real MCP gateway routing
- **Phase 02**: Uses `agents`, `agent_runs` tables for tool call association
- **Phase 03**: Tool calls become visible in CopilotKit chat UI (tool call events stream via AG-UI)

---

## Verification Checklist

- [ ] `uv run alembic upgrade head` — creates tools, agent_tools, tool_calls tables
- [ ] `POST /api/v1/tools` — registers a tool, returns 201
- [ ] `GET /api/v1/tools` — lists tools (includes seeded built-in tools)
- [ ] `POST /api/v1/agents/{id}/tools` — binds tool to agent
- [ ] `GET /api/v1/agents/{id}/tools` — shows bound tools
- [ ] Chat with agent → ask "search for Python tutorials" → agent calls `web_search` tool → mock result appears in chat
- [ ] `tool_calls` table has a record of the tool invocation with timing and status
- [ ] `POST /api/v1/tools/{id}/test` — directly tests tool invocation

---

## Forward-Looking Notes

- **Phase 05** will add a `code_sandbox` MCP tool that wraps the sandbox manager.
- **Phase 06** will wrap `tool_node` to add HITL approval before tool execution — the current `tool_node` function signature must remain stable.
- **Phase 08** will add user-scoped tool namespacing (`mcp://user/{workspace_id}/tool-name`).
- **Phase 09** will add marketplace tools and the `marketplace_tools` table.
- In production, `web_search` should integrate with a real search API (e.g., Tavily, SerpAPI). The mock is sufficient for development.
