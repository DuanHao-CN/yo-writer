# YoAgent — Claude Code Development Guide

## Project Overview

YoAgent is an Agent-as-a-Service platform. Users create, configure, and run AI agents via chat UI or API. Built with FastAPI + LangGraph + CopilotKit + FastMCP.

## Architecture

- **Backend**: `backend/` — FastAPI, Python 3.12+, pyenv + uv
- **Frontend**: `frontend/` — Next.js 15, React 19, CopilotKit
- **Infrastructure**: `infra/` — Docker Compose (dev), Kubernetes (prod)
- **Docs**: `docs/PRD.md` (canonical), `docs/phases/` (implementation guides)
- **Progress**: `docs/PROGRESS.md` — development progress tracker

## Phase-Based Development

Implementation follows `docs/phases/00-index.md` through `docs/phases/10-production.md`. Each phase file is self-contained — read only the current phase file when implementing.

**Key constraint**: Phases 01-07 use hardcoded dev user/workspace (no auth). Auth is Phase 08.

## Python Environment: pyenv + uv

- **pyenv** manages Python version (pinned in `.python-version`)
- **uv** manages packages, venv, and workspace
- The venv uses pyenv's Python interpreter

```bash
# First-time setup
pyenv install 3.12.12       # if not already installed
pyenv local 3.12.12         # .python-version already committed
uv venv --python $(pyenv which python3.12)
uv sync                     # installs all workspace deps
```

## Quick Start

```bash
# 1. Infrastructure (PostgreSQL:5433, Redis:6380, MinIO:9000)
cd infra && docker compose up -d

# 2. Backend
cd backend && uv sync && uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# 3. Frontend
cd frontend && npm install && npm run dev
```

## Development Commands

```bash
# Python (run from backend/)
uv sync                                    # Install dependencies
uv run uvicorn app.main:app --reload       # Start backend
uv run alembic revision --autogenerate -m "description"  # New migration
uv run alembic upgrade head                # Apply migrations
uv run pytest tests/                       # Run tests
uv run ruff check .                        # Lint
uv run ruff format .                       # Format

# Frontend (run from frontend/)
npm run dev                                # Start frontend
npm run build                              # Production build
npm run lint                               # Lint
```

## Code Conventions

- All API routes under `/api/v1/`
- Error responses: `{"error": {"code": "ERROR_CODE", "message": "...", "details": {...}}}`
- Pagination: `?page=1&page_size=20`
- All database operations use async SQLAlchemy sessions
- Use `from app.core.constants import DEV_USER_ID, DEV_WORKSPACE_ID` for phases 01-07
- Keep LangGraph node functions as standalone importable functions (not lambdas)

## Port Mapping (Dev)

| Service | Host Port | Container Port |
|---------|-----------|----------------|
| PostgreSQL | 5433 | 5432 |
| Redis | 6380 | 6379 |
| MinIO API | 9000 | 9000 |
| MinIO Console | 9001 | 9001 |
| Backend API | 8000 | — |
| Frontend | 3000 | — |

## Environment Variables

Required for development (see `.env.example` for full list):
- `DATABASE_URL` — PostgreSQL (default: `postgresql+asyncpg://postgres:secret@localhost:5433/yoagent`)
- `REDIS_URL` — Redis (default: `redis://localhost:6380/0`)
- `OPENAI_API_KEY` — LLM calls (required from Phase 02)

## Testing

- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- E2E tests: `tests/e2e/` (Playwright)
- Always test against real database (Docker Compose PostgreSQL), not mocks
