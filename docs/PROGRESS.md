# YoAgent — Development Progress

> Auto-updated as phases are implemented. Each phase references `docs/phases/XX-*.md`.

---

## Overall Status

| Phase | Title | Status | Completion Date | Notes |
|-------|-------|--------|----------------|-------|
| 00 | Index & Conventions | Done | 2026-03-18 | Master index, tech stack, shared conventions |
| 01 | Project Scaffold | Done | 2026-03-18 | pyenv+uv, FastAPI, Docker Compose, Alembic, Next.js |
| 02 | Agent Core | Done | 2026-03-18 | Agent CRUD, ReAct LangGraph, conversations, checkpointer |
| 03 | Agent Chat UI | Done | 2026-03-18 | CopilotKit, AG-UI streaming |
| 04 | Tool System | Done | 2026-03-18 | FastMCP gateway, Tool CRUD, agent-tool binding, tool call recording |
| 05 | Code Sandbox | Done | 2026-03-18 | Docker sandbox, code execution, MCP tool |
| 06 | Human-in-the-Loop | Done | 2026-03-19 | Approval/edit/review/form patterns |
| 07 | Advanced Agents | Not Started | — | Plan-Execute, Multi-Agent, versioning |
| 08 | Auth & Users | Not Started | — | JWT, OAuth, RBAC |
| 09 | Billing & Marketplace | Not Started | — | Stripe, usage metering |
| 10 | Production | Not Started | — | K8s, gVisor, observability |

---

## Phase 01: Project Scaffold — Done

### Deliverables

- [x] Root `pyproject.toml` — uv workspace with `backend` member
- [x] `.python-version` — pyenv pinned to 3.12.12
- [x] `backend/pyproject.toml` — FastAPI, SQLAlchemy, Alembic, Redis, asyncpg
- [x] `backend/app/main.py` — FastAPI app with `/health`, CORS, error handlers
- [x] `backend/app/core/config.py` — pydantic-settings with DB pool config
- [x] `backend/app/core/database.py` — async SQLAlchemy engine + session
- [x] `backend/app/core/constants.py` — DEV_USER_ID, DEV_WORKSPACE_ID
- [x] `backend/app/core/errors.py` — APIError class + exception handlers
- [x] `backend/alembic.ini` + `migrations/env.py` — Alembic configured with Base.metadata
- [x] `backend/Dockerfile` — multistage build with uv
- [x] `infra/docker-compose.yml` — PostgreSQL(5433), Redis(6380), MinIO(9000/9001)
- [x] `frontend/` — Next.js 15 app with landing page
- [x] `.env.example` + `.env` — all env vars documented
- [x] `CLAUDE.md` — development guide with pyenv+uv setup
- [x] Empty `__init__.py` for all packages: models, schemas, services, api/v1, runtime/graphs

### Verification Results

- [x] `docker compose up -d` — 3 services healthy (db, redis, minio)
- [x] `uv sync` — all dependencies installed via pyenv Python 3.12.12
- [x] `uv run alembic upgrade head` — migration applied, `alembic_version` table exists
- [x] `curl /health` → `{"status":"ok","version":"0.1.0"}`
- [x] `npm run build` — Next.js builds successfully
- [x] PostgreSQL connectable, Redis responds PONG

### Port Mapping

| Service | Port |
|---------|------|
| PostgreSQL | localhost:5433 |
| Redis | localhost:6380 |
| MinIO | localhost:9000 / 9001 |

---

## Phase 02: Agent Core — Done

### Deliverables

- [x] SQLAlchemy models: Agent, AgentVersion, Conversation, Message, AgentRun (`backend/app/models/agent.py`)
- [x] Models `__init__.py` with all imports (`backend/app/models/__init__.py`)
- [x] Alembic migration creating 5 tables + nullable fix (`backend/migrations/versions/`)
- [x] Pydantic schemas for Agent CRUD (`backend/app/schemas/agent.py`)
- [x] Pydantic schemas for Conversation/Message (`backend/app/schemas/conversation.py`)
- [x] Agent service with CRUD + slug generation (`backend/app/services/agent_service.py`)
- [x] Conversation service with CRUD + messages (`backend/app/services/conversation_service.py`)
- [x] Agent CRUD API routes (`backend/app/api/v1/agents.py`)
- [x] Conversation API routes (`backend/app/api/v1/conversations.py`)
- [x] ReAct LangGraph graph with mock tool node (`backend/app/runtime/graphs/react.py`)
- [x] AsyncPostgresSaver checkpointer (`backend/app/runtime/checkpointer.py`)
- [x] AgentRuntime engine (`backend/app/runtime/engine.py`)
- [x] Routers registered in `backend/app/main.py`
- [x] OPENAI_API_KEY config added to Settings
- [x] Alembic env.py excludes LangGraph checkpoint tables
- [x] `psycopg[binary]` added to dependencies

### Verification Results

- [x] `uv run alembic upgrade head` — 5 tables created (agents, agent_versions, conversations, messages, agent_runs)
- [x] `POST /api/v1/agents` — creates agent, returns 201 with ID, slug, timestamps
- [x] `GET /api/v1/agents` — lists agents in dev workspace with pagination
- [x] `GET /api/v1/agents/{id}` — returns agent details
- [x] `PATCH /api/v1/agents/{id}` — updates agent fields (description, status)
- [x] `DELETE /api/v1/agents/{id}` — deletes agent, returns 204
- [x] Slug conflict returns 409 with `AGENT_SLUG_CONFLICT` error
- [x] `POST /api/v1/conversations` — creates conversation linked to agent
- [x] `POST /api/v1/conversations/{id}/messages` — stores message
- [x] `GET /api/v1/conversations/{id}` — returns conversation with messages (selectinload)
- [x] `GET /api/v1/conversations/{id}/messages` — returns message history
- [x] `POST /api/v1/agents/{id}/run` — runtime wired (requires OPENAI_API_KEY in `.env`)

### Note

Agent run endpoint (`POST /api/v1/agents/{id}/run`) requires `OPENAI_API_KEY` set in `.env`. Uncomment and fill the key to enable LLM execution.

---

## Phase 03: Agent Chat UI — Done

### Deliverables

- [x] `OPENAI_BASE_URL` config added to Settings + `.env` / `.env.example`
- [x] `base_url` passed to `ChatOpenAI()` in ReAct graph (`backend/app/runtime/graphs/react.py`)
- [x] `copilotkit` + `ag-ui-langgraph` added to backend dependencies
- [x] Persistent checkpointer lifecycle: `init_checkpointer()` / `close_checkpointer()` / `get_persistent_checkpointer()` (`backend/app/runtime/checkpointer.py`)
- [x] `AgentRuntime.graphs` dict + `register_agent()` method for pre-compiled graphs (`backend/app/runtime/engine.py`)
- [x] CopilotKit endpoint via `CopilotKitRemoteEndpoint` + `LangGraphAgent` (`backend/app/api/agui.py`)
- [x] Lifespan startup loads all agents → registers graphs → mounts `/copilotkit` endpoint (`backend/app/main.py`)
- [x] `@copilotkit/react-core` + `@copilotkit/react-ui` installed in frontend
- [x] Agent list page at `/agents` — fetches from API, renders cards linking to chat (`frontend/app/agents/page.tsx`)
- [x] Chat layout with CopilotKit provider per agent slug (`frontend/app/chat/[agent_slug]/layout.tsx`)
- [x] Chat page with `AgentChat` component (`frontend/app/chat/[agent_slug]/page.tsx`)
- [x] `AgentChat` generative UI component with `render_chart` + `show_code_result` actions (`frontend/app/components/copilot/AgentChat.tsx`)
- [x] Landing page updated with "View Agents" link (`frontend/app/page.tsx`)

### Architecture Notes

- CopilotKit uses `CopilotKitRemoteEndpoint` (single `/copilotkit` endpoint for all agents)
- Frontend selects agent via `agent` prop on `<CopilotKit>` provider
- langgraph pinned at `>=1.0` (1.0.10 installed) for copilotkit compatibility
- Persistent checkpointer shared across all compiled graphs (initialized once at startup)

---

## Phase 04: Tool System — Done

### Deliverables

- [x] CopilotKit `showDevConsole={false}` — suppresses `announcements.json` fetch error (`frontend/app/chat/[agent_slug]/layout.tsx`)
- [x] `fastmcp>=2.0` added to backend dependencies (`backend/pyproject.toml`)
- [x] SQLAlchemy models: Tool, AgentTool, ToolCall (`backend/app/models/tool.py`)
- [x] Models `__init__.py` updated with tool model imports
- [x] Alembic migration creating `tools`, `agent_tools`, `tool_calls` tables with indexes
- [x] Pydantic schemas: ToolCreate, ToolUpdate, ToolResponse, ToolListResponse, AgentToolBind, AgentToolResponse, ToolTestRequest, ToolTestResponse (`backend/app/schemas/tool.py`)
- [x] FastMCP gateway with builtin web-search and file-ops mock tools (`backend/app/runtime/mcp_gateway.py`)
- [x] ReAct graph `tool_node` replaced with real MCP gateway routing (`backend/app/runtime/graphs/react.py`)
- [x] Tool service with CRUD, test, bind/unbind, seed builtins (`backend/app/services/tool_service.py`)
- [x] Tool CRUD API routes (`backend/app/api/v1/tools.py`)
- [x] Agent-tool binding endpoints added to agents router (`backend/app/api/v1/agents.py`)
- [x] Tools router registered + builtin tools seeded at startup (`backend/app/main.py`)

### Verification Results

- [x] `uv sync` — fastmcp 3.1.1 installed
- [x] `uv run alembic upgrade head` — tools, agent_tools, tool_calls tables created
- [x] `GET /api/v1/tools` — returns 2 seeded builtin tools (web-search, file-ops)
- [x] `POST /api/v1/tools` — creates custom tool, returns 201
- [x] `POST /api/v1/agents/{id}/tools` — binds tool to agent
- [x] `GET /api/v1/agents/{id}/tools` — returns bound tools with tool details
- [x] `DELETE /api/v1/agents/{id}/tools/{tool_id}` — unbinds tool, returns 204
- [x] `DELETE /api/v1/tools/{id}` — deletes tool, returns 204
- [x] `POST /api/v1/tools/{id}/test` — invokes tool via MCP gateway, returns mock result + timing
- [x] ReAct graph tool_node calls MCP gateway instead of returning mock strings

### Architecture Notes

- FastMCP gateway uses `Client(gateway)` in-memory pattern (no network transport)
- Namespace separator is underscore (`builtin_web-search_web_search`) per MCP tool naming spec
- MCP tool schemas are cached at module level after first LLM binding fetch
- Tool node function signature kept stable for Phase 06 HITL wrapping

---

## Phase 05: Code Sandbox — Done

### Deliverables

- [x] Sandbox config dataclasses: `SandboxConfig`, `ExecutionResult` (`backend/app/runtime/sandbox/config.py`)
- [x] `SandboxManager` with Docker-based execution, resource limits, timeout handling (`backend/app/runtime/sandbox/manager.py`)
- [x] `code_sandbox` MCP tool mounted on gateway as `builtin_code-sandbox` (`backend/app/runtime/mcp_gateway.py`)
- [x] SQLAlchemy model: `SandboxExecution` (`backend/app/models/sandbox.py`)
- [x] Alembic migration creating `sandbox_executions` table with index on `agent_run_id`
- [x] Pydantic schemas: `SandboxExecuteRequest`, `SandboxExecuteResponse` (`backend/app/schemas/sandbox.py`)
- [x] Sandbox service: `execute_code()`, `record_execution()` (`backend/app/services/sandbox_service.py`)
- [x] Dev endpoint: `POST /api/v1/sandbox/execute` (`backend/app/api/v1/sandbox.py`)
- [x] Seeded `code-sandbox` builtin tool in `seed_builtin_tools()`
- [x] Sandbox router registered in `app.main`

### Verification Results

- [x] `uv run alembic upgrade head` — `sandbox_executions` table created
- [x] `docker pull python:3.12-slim` — sandbox base image available
- [x] `POST /api/v1/sandbox/execute` with `{"code": "print(2+2)"}` → `{"stdout": "4\n", "exit_code": 0}`
- [x] Timeout: `{"code": "import time; time.sleep(60)"}` → killed after timeout, exit_code=137
- [x] Memory: `{"code": "x = bytearray(600*1024*1024)"}` → OOM killed, exit_code=137
- [x] Network disabled: `urllib.request.urlopen('http://example.com')` → name resolution failure
- [x] `GET /api/v1/tools/` — shows seeded code-sandbox builtin tool
- [x] MCP gateway exposes `builtin_code-sandbox_code_sandbox` tool

### Architecture Notes

- Docker run with `--rm --memory --memory-swap --cpus=1 --pids-limit=10 --read-only --network=none`
- Tmpfs mounts for `/tmp` and `/workspace` (100m each)
- Package install uses `pip` (available in python:3.12-slim), enables network temporarily
- Timeout via `asyncio.wait_for` + process kill on expiry
- Dev-mode isolation (Docker); Phase 10 upgrades to gVisor

---

## Phase 06: Human-in-the-Loop — Done

### Deliverables

- [x] HITL-enhanced tool node with approval/review/execute routing (`backend/app/runtime/graphs/react_hitl.py`)
- [x] `HITLConfig` schema (require_approval, require_review lists) added to `AgentConfig` (`backend/app/schemas/agent.py`)
- [x] Conditional graph selection: HITL graph when approval/review configured, standard ReAct otherwise (`backend/app/runtime/engine.py`)
- [x] `HITLApproval` component: Approve/Reject/Edit&Approve buttons with JSON args editor (`frontend/app/components/hitl/HITLApproval.tsx`)
- [x] `HITLReview` component: editable textarea with original output + Accept & Continue (`frontend/app/components/hitl/HITLReview.tsx`)
- [x] `HITLFormInput` component: dynamic form from fields schema (select for enums, input for strings) (`frontend/app/components/hitl/HITLFormInput.tsx`)
- [x] `useLangGraphInterrupt` registered in AgentChat with type-based routing to HITL components (`frontend/app/components/copilot/AgentChat.tsx`)

### Architecture Notes

- Uses LangGraph `interrupt()` from `langgraph.types` — checkpoint-based suspension, no timeouts needed
- `resolve()` takes a string — frontend JSON.stringifies, backend JSON.loads on resume
- HITL config is part of agent config dict, no new DB tables needed
- Agents without HITL config use standard `build_react_graph()` — zero overhead for non-HITL agents
- Three HITL patterns: approval (pre-execution gate), review (post-execution edit), form_input (structured human input)

---

## Next Step

**Phase 07: Advanced Agents** — Read `docs/phases/07-advanced-agents.md` and implement.
