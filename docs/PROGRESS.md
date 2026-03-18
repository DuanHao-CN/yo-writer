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
| 04 | Tool System | Not Started | — | FastMCP gateway, built-in tools |
| 05 | Code Sandbox | Not Started | — | Docker sandbox, code execution |
| 06 | Human-in-the-Loop | Not Started | — | Approval/edit/review/form patterns |
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

## Next Step

**Phase 04: Tool System** — Read `docs/phases/04-tools.md` and implement.
