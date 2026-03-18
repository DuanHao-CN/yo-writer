# Phase 01: Project Scaffold

## Meta

| Field | Value |
|-------|-------|
| **Goal** | Set up repository structure, Docker infrastructure, and basic health checks |
| **Prerequisites** | None |
| **Effort** | 1-2 days |
| **Key Technologies** | uv, FastAPI, Next.js, Docker Compose, PostgreSQL, Redis, MinIO, Alembic |

---

## Context

This phase creates the foundational project structure for the YoAgent platform. We set up a Python monorepo managed by `uv` workspaces, Docker Compose for local infrastructure (PostgreSQL with pgvector, Redis, MinIO), a minimal FastAPI backend with a `/health` endpoint, and a minimal Next.js frontend landing page. No business logic yet — just verified connectivity between all layers.

Phases 01-07 operate without authentication. We use hardcoded dev constants:

```python
# backend/app/core/constants.py
DEV_USER_ID = "00000000-0000-0000-0000-000000000001"
DEV_WORKSPACE_ID = "00000000-0000-0000-0000-000000000002"
```

---

## Data Models

No application tables in this phase. Alembic is initialized with an empty migration to verify the migration pipeline works.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Returns `{"status": "ok", "version": "0.1.0"}` |

---

## Implementation Steps

### Step 1: Root project configuration

**File**: `pyproject.toml` (root)

```toml
[project]
name = "yo-agent"
version = "0.1.0"
requires-python = ">=3.12"

[tool.uv.workspace]
members = ["backend", "mcp-gateway", "sandbox"]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.4",
]
```

### Step 2: Backend FastAPI skeleton

**File**: `backend/pyproject.toml`

```toml
[project]
name = "yo-agent-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.30",
    "alembic>=1.13",
    "pydantic-settings>=2.0",
    "redis>=5.0",
]
```

**File**: `backend/app/__init__.py` — empty

**File**: `backend/app/main.py`

```python
from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(title="YoAgent API", version=settings.VERSION)

@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.VERSION}
```

**File**: `backend/app/core/__init__.py` — empty

**File**: `backend/app/core/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    VERSION: str = "0.1.0"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:secret@localhost:5432/yoagent"
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()
```

**File**: `backend/app/core/constants.py`

```python
DEV_USER_ID = "00000000-0000-0000-0000-000000000001"
DEV_WORKSPACE_ID = "00000000-0000-0000-0000-000000000002"
```

**File**: `backend/app/core/database.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
```

### Step 3: Alembic setup

```bash
cd backend && uv run alembic init migrations
```

**File**: `backend/alembic.ini` — set `sqlalchemy.url` to use env var
**File**: `backend/migrations/env.py` — configure to use `app.core.database.Base.metadata`

### Step 4: Docker Compose infrastructure

**File**: `infra/docker-compose.yml`

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: yoagent
      POSTGRES_PASSWORD: secret
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio
    ports: ["9000:9000", "9001:9001"]
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio-data:/data

volumes:
  pgdata:
  minio-data:
```

### Step 5: Frontend skeleton

**File**: `frontend/package.json`

```json
{
  "name": "yo-agent-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "^15",
    "react": "^19",
    "react-dom": "^19"
  },
  "devDependencies": {
    "@types/node": "^22",
    "@types/react": "^19",
    "typescript": "^5"
  }
}
```

**File**: `frontend/src/app/page.tsx`

```tsx
export default function Home() {
  return (
    <main style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
      <h1>YoAgent</h1>
    </main>
  );
}
```

**File**: `frontend/src/app/layout.tsx`

```tsx
export const metadata = { title: "YoAgent" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

### Step 6: Backend Dockerfile

**File**: `backend/Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY app/ app/
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Integration Points

None — this is the foundational phase.

---

## Verification Checklist

- [ ] `cd infra && docker compose up -d` — all 3 services healthy
- [ ] `cd backend && uv sync` — dependencies install
- [ ] `cd backend && uv run uvicorn app.main:app --reload` — server starts
- [ ] `curl http://localhost:8000/health` → `{"status":"ok","version":"0.1.0"}`
- [ ] `cd backend && uv run alembic upgrade head` — migration runs (no-op)
- [ ] `cd frontend && npm install && npm run dev` — Next.js renders at `http://localhost:3000`
- [ ] PostgreSQL accepts connections: `psql -h localhost -U postgres -d yoagent`
- [ ] Redis responds: `redis-cli ping` → `PONG`

---

## Forward-Looking Notes

- **Phase 02** will add SQLAlchemy models to `backend/app/models/` and register them in `Base.metadata` for Alembic auto-generation.
- **Phase 03** will add CopilotKit dependencies to `frontend/package.json`.
- Keep the `infra/docker-compose.yml` focused on infrastructure only — app services (api, mcp-gateway, sandbox-manager) will be added later for production parity but are run locally via `uv run` during development.
