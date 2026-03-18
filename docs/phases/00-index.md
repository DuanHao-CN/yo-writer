# YoAgent — Phase-Based Implementation Index

> **Project Codename**: YoAgent
> **Canonical Reference**: `docs/PRD.md` (preserved, do not modify)
> **Architecture**: Agent-as-a-Service platform

---

## Dependency Graph

```
01 scaffold → 02 agent-core → 03 agent-chat → 04 tool-system → 05 sandbox
                                                                      ↓
                                                   06 hitl → 07 advanced-agents
                                                                      ↓
                                              08 auth-users → 09 billing → 10 production
```

Phases 01-07 = core experience (no auth, hardcoded dev user/workspace).
Phases 08-10 = productionize.

---

## Phase Summary

| Phase | Title | Goal | Prerequisites | Effort |
|-------|-------|------|---------------|--------|
| 01 | Project Scaffold | Repo structure, Docker infra, health checks | None | 1-2 days |
| 02 | Agent Core | Agent data model, ReAct LangGraph, agent CRUD | 01 | 2-3 days |
| 03 | Agent Chat UI | CopilotKit + AG-UI streaming chat | 02 | 2-3 days |
| 04 | Tool System | FastMCP gateway, built-in tools, tool CRUD | 02 | 2-3 days |
| 05 | Code Sandbox | Docker-based sandbox, code execution MCP tool | 04 | 2-3 days |
| 06 | Human-in-the-Loop | Approval/edit/review/form-input patterns | 02, 03 | 2-3 days |
| 07 | Advanced Agents | Plan-Execute, Multi-Agent, versioning | 05, 06 | 3-4 days |
| 08 | Auth & Users | JWT, OAuth, RBAC, workspace isolation | 07 | 3-4 days |
| 09 | Billing & Marketplace | Stripe, usage metering, tool marketplace | 08 | 3-4 days |
| 10 | Production | K8s, gVisor, observability, autoscaling | 09 | 4-5 days |

---

## Tech Stack

| Layer | Technology | Role |
|-------|-----------|------|
| **Frontend** | Next.js + CopilotKit | Agent Chat UI, Generative UI, Agent Builder |
| **API Gateway** | Traefik / Nginx | Routing, rate limiting, SSL, load balancing |
| **Backend** | FastAPI (Python) | REST API, WebSocket, AG-UI Endpoint |
| **Agent Orchestration** | LangGraph | StateGraph, conditional branching, multi-agent |
| **Tool Protocol** | FastMCP | MCP tool registry, discovery, routing, auth |
| **Code Sandbox** | Docker containers (dev) / gVisor (prod) | Isolated Python code execution |
| **Package Manager** | uv | Python dependency installation & venv management |
| **Database** | PostgreSQL + pgvector | Structured data + vector search |
| **Cache** | Redis | Session cache, rate limit counters, PubSub |
| **Object Storage** | S3 / MinIO | File uploads, agent artifact storage |
| **Message Queue** | Redis Streams / NATS | Async task dispatch, agent event streams |
| **Observability** | OpenTelemetry + Grafana | Distributed tracing, metrics, log aggregation |

---

## Shared Conventions

### Project Structure

```
yo-agent/
├── frontend/                     # Next.js + CopilotKit
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   └── hooks/
│   ├── package.json
│   └── next.config.js
├── backend/                      # FastAPI
│   ├── app/
│   │   ├── main.py               # FastAPI entry point
│   │   ├── api/                   # API routes
│   │   │   ├── v1/
│   │   │   │   ├── agents.py
│   │   │   │   ├── tools.py
│   │   │   │   ├── conversations.py
│   │   │   │   └── auth.py
│   │   │   └── agui.py           # AG-UI endpoint
│   │   ├── core/                  # Core config
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── database.py
│   │   ├── models/                # SQLAlchemy models
│   │   ├── schemas/               # Pydantic schemas
│   │   ├── services/              # Business logic
│   │   └── runtime/               # Agent runtime
│   │       ├── engine.py          # LangGraph orchestration
│   │       ├── graphs/            # Graph patterns
│   │       │   ├── react.py
│   │       │   ├── plan_execute.py
│   │       │   └── multi_agent.py
│   │       └── checkpointer.py
│   ├── pyproject.toml
│   └── uv.lock
├── mcp-gateway/                   # FastMCP tool gateway
│   ├── gateway/
│   │   ├── main.py
│   │   ├── router.py
│   │   ├── middleware.py
│   │   └── builtin/               # Built-in MCP Servers
│   │       ├── code_sandbox.py
│   │       ├── file_ops.py
│   │       ├── web_search.py
│   │       └── vector_store.py
│   └── pyproject.toml
├── sandbox/                       # Sandbox manager
│   ├── manager/
│   │   ├── main.py
│   │   ├── pool.py
│   │   ├── executor.py
│   │   └── security.py
│   └── pyproject.toml
├── infra/                         # Infrastructure
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── k8s/
│       ├── base/
│       └── overlays/
│           ├── dev/
│           └── prod/
├── migrations/                    # Alembic database migrations
│   ├── alembic.ini
│   └── versions/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
│   ├── PRD.md                     # Canonical reference
│   └── phases/                    # This directory
├── pyproject.toml                 # Root project (workspace)
└── README.md
```

### Development Conventions

- **Package manager**: `uv` for all Python projects
- **Python version**: 3.12+
- **Backend framework**: FastAPI with async endpoints
- **Database migrations**: Alembic
- **API prefix**: `/api/v1/`
- **Pagination**: `?page=1&page_size=20` → response includes `total`, `page`, `page_size`
- **Dev user/workspace**: Phases 01-07 use hardcoded `DEV_USER_ID` and `DEV_WORKSPACE_ID` UUIDs
- **Linting/Formatting**: `ruff` for Python, `eslint` + `prettier` for TypeScript

### Error Handling Standard

All API errors use this format:

```json
{
  "error": {
    "code": "AGENT_NOT_FOUND",
    "message": "Agent with ID xxx does not exist",
    "details": {"agent_id": "xxx"},
    "request_id": "req_abc123"
  }
}
```

**Error code registry** (each phase extends this):

| Code | HTTP Status | Phase | Description |
|------|-------------|-------|-------------|
| `VALIDATION_ERROR` | 400 | 01+ | Request body validation failed |
| `NOT_FOUND` | 404 | 01+ | Resource not found |
| `INTERNAL_ERROR` | 500 | 01+ | Unexpected server error |
| `AGENT_NOT_FOUND` | 404 | 02 | Agent does not exist |
| `AGENT_RUN_FAILED` | 500 | 02 | Agent execution failed |
| `CONVERSATION_NOT_FOUND` | 404 | 02 | Conversation does not exist |
| `TOOL_NOT_FOUND` | 404 | 04 | Tool does not exist |
| `TOOL_CALL_FAILED` | 502 | 04 | Tool call returned error |
| `SANDBOX_TIMEOUT` | 408 | 05 | Code execution timed out |
| `SANDBOX_OOM` | 413 | 05 | Code exceeded memory limit |
| `HITL_TIMEOUT` | 408 | 06 | User did not respond to approval in time |
| `AUTH_INVALID_TOKEN` | 401 | 08 | JWT expired or malformed |
| `AUTH_FORBIDDEN` | 403 | 08 | Insufficient RBAC permissions |
| `RATE_LIMIT_EXCEEDED` | 429 | 09 | Plan rate limit exceeded |
| `QUOTA_EXCEEDED` | 429 | 09 | Usage quota exhausted for billing period |

**Implementation**: A shared `APIError` exception class + FastAPI exception handler:

```python
# backend/app/core/errors.py
class APIError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
```

### Resilience Patterns

**Retry with exponential backoff** (for LLM calls, external tool calls):
- Base: 1s, multiplier: 2x, max: 16s, jitter: random 0-1s
- Max retries: 3 for LLM, 2 for tools, 0 for sandbox

**Circuit breaker** (for LLM providers):
- Failure threshold: 5 consecutive failures → circuit OPEN
- Open duration: 30s → switch to HALF_OPEN → test with 1 request
- Fallback: switch to secondary LLM provider if configured

**Timeouts by operation**:

| Operation | Timeout | Retry |
|-----------|---------|-------|
| LLM call | 60s | 3x backoff |
| Tool call (built-in) | 10s | 2x backoff |
| Tool call (external) | 30s | 2x backoff |
| Sandbox execution | configurable (default 30s) | no retry |
| Database query | 5s | 1x immediate |
| HITL approval wait | 5min | no retry, auto-reject |

### LLM Provider Abstraction

All LLM calls go through an abstraction layer that handles provider switching:

```python
# backend/app/runtime/llm_provider.py
class LLMProvider:
    """Unified interface for LLM providers with failover."""
    async def invoke(self, messages, model_config, fallback_provider=None):
        try:
            return await self._call_primary(messages, model_config)
        except (RateLimitError, ProviderUnavailableError):
            if fallback_provider:
                return await self._call_fallback(messages, model_config, fallback_provider)
            raise
```

Supported providers: `openai`, `anthropic`, `custom` (OpenAI-compatible endpoint).

### Database Connection Pool

```python
# All environments use these pool settings
DATABASE_POOL_SIZE = 20        # base pool connections
DATABASE_MAX_OVERFLOW = 10     # extra connections above pool size
DATABASE_POOL_TIMEOUT = 30     # seconds to wait for connection
DATABASE_POOL_RECYCLE = 3600   # recycle connections after 1 hour
```

### Environment Variables

| Variable | Required | Default | Phase | Description |
|----------|----------|---------|-------|-------------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://postgres:secret@localhost:5432/yoagent` | 01 | PostgreSQL connection |
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | 01 | Redis connection |
| `OPENAI_API_KEY` | Yes | — | 02 | OpenAI API key for LLM calls |
| `ANTHROPIC_API_KEY` | No | — | 02 | Anthropic API key (fallback LLM) |
| `DEFAULT_LLM_PROVIDER` | No | `openai` | 02 | Default LLM provider |
| `DEFAULT_LLM_MODEL` | No | `gpt-5.4` | 02 | Default model ID |
| `FRONTEND_URL` | No | `http://localhost:3000` | 03 | Frontend origin for CORS |
| `HITL_TIMEOUT_SECONDS` | No | `300` | 06 | Auto-reject after N seconds |
| `JWT_SECRET_KEY` | Yes (Phase 08+) | — | 08 | RS256 private key for JWT signing |
| `JWT_PUBLIC_KEY` | Yes (Phase 08+) | — | 08 | RS256 public key for JWT verification |
| `GITHUB_CLIENT_ID` | No | — | 08 | GitHub OAuth app ID |
| `GITHUB_CLIENT_SECRET` | No | — | 08 | GitHub OAuth secret |
| `GOOGLE_CLIENT_ID` | No | — | 08 | Google OAuth app ID |
| `GOOGLE_CLIENT_SECRET` | No | — | 08 | Google OAuth secret |
| `FERNET_KEY` | Yes (Phase 08+) | — | 08 | Encryption key for tool credentials |
| `STRIPE_SECRET_KEY` | Yes (Phase 09+) | — | 09 | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | Yes (Phase 09+) | — | 09 | Stripe webhook signing secret |
| `STRIPE_PRO_PRICE_ID` | Yes (Phase 09+) | — | 09 | Stripe Pro plan price ID |
| `STRIPE_TEAM_PRICE_ID` | Yes (Phase 09+) | — | 09 | Stripe Team plan price ID |
| `OTEL_ENDPOINT` | No | `http://localhost:4317` | 10 | OpenTelemetry collector gRPC endpoint |
| `SANDBOX_RUNTIME` | No | `runc` | 05 (10 for gVisor) | Docker runtime (`runc` dev, `runsc` prod) |

### Cache Strategy

| Data | TTL | Invalidation | Phase |
|------|-----|--------------|-------|
| Agent config | 1h | On PATCH/DELETE agent | 02 |
| Tool schemas | 30min | On tool update/install | 04 |
| User session | 15min (matches JWT) | On logout/token refresh | 08 |
| Rate limit counters | 1min sliding window | Auto-expire | 09 |
| Usage aggregates | 5min | On new usage record | 09 |

Key pattern: `{type}:{id}[:v{version}]` — e.g., `agent:uuid:v3`, `tool:uuid`

### Data Model Partitioning

| Phase | Tables Introduced |
|-------|-------------------|
| 02 | agents, agent_versions, conversations, messages, agent_runs |
| 04 | tools, agent_tools, tool_calls |
| 05 | sandbox_executions |
| 08 | users, workspaces, workspace_members, api_keys |
| 09 | usage_records, marketplace_tools |

---

## ADR Summary

| ADR | Decision | Rationale |
|-----|----------|-----------|
| ADR-001 | AG-UI Protocol over direct WebSocket | Standardized CopilotKit protocol with built-in LangGraph state sync |
| ADR-002 | FastMCP Gateway over direct tool calls | Unified discovery, routing, auth, audit, and rate limiting |
| ADR-003 | gVisor over Docker-in-Docker for sandbox | Smaller attack surface than native Linux kernel, lighter than full VM |

---

## Phase File Template

Every phase file follows this structure:

```
# Phase XX: [Title]
## Meta (goal, prerequisites, effort, key technologies)
## Context (self-contained background)
## Data Models (SQL CREATE TABLE for this phase's tables)
## API Endpoints (full endpoint list with example JSON)
## Implementation Steps (numbered, with file paths + code patterns)
## Integration Points (how this connects to prior phases)
## Verification Checklist (commands + expected results)
## Forward-Looking Notes (prep for future phases)
```
