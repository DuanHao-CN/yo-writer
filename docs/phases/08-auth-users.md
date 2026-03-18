# Phase 08: Authentication & Workspace Isolation

## Meta

| Field | Value |
|-------|-------|
| **Goal** | JWT auth, OAuth, RBAC, workspace isolation — retrofit auth into all existing endpoints |
| **Prerequisites** | Phase 07 (all core features complete) |
| **Effort** | 3-4 days |
| **Key Technologies** | JWT (RS256), OAuth 2.0, bcrypt, Fernet encryption, FastAPI Depends |

---

## Context

Phases 01-07 used hardcoded `DEV_USER_ID` and `DEV_WORKSPACE_ID`. This phase introduces real authentication, user management, and workspace-based multi-tenancy.

After this phase:
- Users register/login with email+password or OAuth (GitHub, Google)
- JWT access tokens (15min) + refresh tokens (7d) protect all API endpoints
- API keys (`ya_` prefix) enable programmatic access
- RBAC (Owner/Admin/Member/Viewer) controls workspace permissions
- All existing endpoints get `Depends(get_current_user)` for tenant isolation
- Credential Manager encrypts tool credentials per workspace

### Multi-Tenant Isolation Model

```
Platform
├── Tenant A (Workspace)
│   ├── Data: row-level isolation (workspace_id WHERE clause)
│   ├── MCP Tools: namespace isolation (user/{workspace_id}/*)
│   ├── Sandbox: process-level isolation
│   ├── API Keys: workspace-bound
│   └── Billing: independent metering
├── Tenant B (Workspace)
│   └── ...
└── Platform (Shared)
    ├── Built-in Tools: shared read-only
    └── LLM Providers: shared connection pool
```

---

## Data Models

### Alembic Migration

```sql
-- Users
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255),
    display_name    VARCHAR(100),
    avatar_url      TEXT,
    auth_provider   VARCHAR(50) DEFAULT 'email',  -- email | github | google
    external_id     VARCHAR(255),                  -- OAuth provider user ID
    plan            VARCHAR(20) DEFAULT 'free',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Workspaces
CREATE TABLE workspaces (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    slug            VARCHAR(100) UNIQUE NOT NULL,
    owner_id        UUID REFERENCES users(id) ON DELETE CASCADE,
    settings        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Workspace Members
CREATE TABLE workspace_members (
    workspace_id    UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL DEFAULT 'member',
    -- role: owner | admin | member | viewer
    joined_at       TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (workspace_id, user_id)
);

-- API Keys
CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    workspace_id    UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    name            VARCHAR(100),
    key_hash        VARCHAR(255) NOT NULL,   -- bcrypt hash
    key_prefix      VARCHAR(10) NOT NULL,    -- "ya_" + first 8 chars
    scopes          TEXT[] DEFAULT '{}',
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### Add Foreign Keys to Existing Tables

Migration to add FK constraints to tables from Phases 02, 04, 05:

```sql
-- agents.workspace_id → workspaces(id)
ALTER TABLE agents ADD CONSTRAINT fk_agents_workspace
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;

-- conversations.user_id → users(id)
ALTER TABLE conversations ADD CONSTRAINT fk_conversations_user
    FOREIGN KEY (user_id) REFERENCES users(id);

-- agent_versions.created_by → users(id)
ALTER TABLE agent_versions ADD CONSTRAINT fk_agent_versions_created_by
    FOREIGN KEY (created_by) REFERENCES users(id);

-- tools.workspace_id → workspaces(id)
ALTER TABLE tools ADD CONSTRAINT fk_tools_workspace
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;
```

---

## API Endpoints

### Auth

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register with email+password |
| POST | `/api/v1/auth/login` | Login, returns JWT + refresh token |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET | `/api/v1/auth/me` | Get current user profile |
| GET | `/api/v1/auth/github` | GitHub OAuth redirect |
| GET | `/api/v1/auth/github/callback` | GitHub OAuth callback |
| GET | `/api/v1/auth/google` | Google OAuth redirect |
| GET | `/api/v1/auth/google/callback` | Google OAuth callback |

**Register Request**:

```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "display_name": "John Doe"
}
```

**Login Response**:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### API Keys

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/api-keys` | Create API key (returns raw key once) |
| GET | `/api/v1/api-keys` | List API keys (prefix only) |
| DELETE | `/api/v1/api-keys/{key_id}` | Revoke API key |

**Create Key Response** (raw key shown only once):

```json
{
  "id": "uuid",
  "key": "ya_sk_abc12345...",
  "name": "My CI Key",
  "key_prefix": "ya_sk_abc1",
  "scopes": ["agents:read", "agents:run"],
  "created_at": "2026-03-17T10:00:00Z"
}
```

### Workspaces

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/workspaces` | Create workspace |
| GET | `/api/v1/workspaces` | List user's workspaces |
| GET | `/api/v1/workspaces/{ws_id}` | Get workspace details |
| POST | `/api/v1/workspaces/{ws_id}/members` | Invite member |
| GET | `/api/v1/workspaces/{ws_id}/members` | List members |
| PATCH | `/api/v1/workspaces/{ws_id}/members/{user_id}` | Update member role |
| DELETE | `/api/v1/workspaces/{ws_id}/members/{user_id}` | Remove member |

---

## Implementation Steps

### Step 1: Security Utilities

**File**: `backend/app/core/security.py`

```python
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    payload = {"sub": user_id, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="RS256")

def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=7)
    payload = {"sub": user_id, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="RS256")

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_PUBLIC_KEY, algorithms=["RS256"])
```

### Step 2: Auth Dependencies

**File**: `backend/app/core/auth.py`

```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    api_key: str | None = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate via JWT Bearer token or X-API-Key header."""
    if credentials:
        try:
            payload = decode_token(credentials.credentials)
            user = await get_user_by_id(db, payload["sub"])
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            return user
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    if api_key and api_key.startswith("ya_"):
        user = await authenticate_api_key(db, api_key)
        if user:
            return user

    raise HTTPException(status_code=401, detail="Not authenticated")

async def require_workspace_role(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    min_role: str = "viewer",
) -> WorkspaceMember:
    """Check user has required role in workspace."""
    member = await get_workspace_member(db, workspace_id, user.id)
    if not member:
        raise HTTPException(status_code=403, detail="Not a workspace member")
    role_hierarchy = {"viewer": 0, "member": 1, "admin": 2, "owner": 3}
    if role_hierarchy[member.role] < role_hierarchy[min_role]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return member
```

### Step 3: Auth Service & Routes

**File**: `backend/app/services/auth_service.py`
**File**: `backend/app/api/v1/auth.py`

Registration, login, OAuth flows, token refresh.

### Step 4: API Key Service

**File**: `backend/app/services/api_key_service.py`

```python
import secrets

async def create_api_key(db: AsyncSession, user_id: UUID, workspace_id: UUID, name: str, scopes: list[str]) -> tuple[ApiKey, str]:
    raw_key = f"ya_sk_{secrets.token_urlsafe(32)}"
    key_hash = pwd_context.hash(raw_key)
    key_prefix = raw_key[:12]

    api_key = ApiKey(
        user_id=user_id,
        workspace_id=workspace_id,
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=scopes,
    )
    db.add(api_key)
    await db.commit()
    return api_key, raw_key  # raw_key returned only once
```

### Step 5: Credential Manager

**File**: `backend/app/core/credential_manager.py`

```python
from cryptography.fernet import Fernet
import json

class CredentialManager:
    def __init__(self, encryption_key: bytes):
        self.cipher = Fernet(encryption_key)

    async def store(self, db: AsyncSession, workspace_id: UUID, tool_id: UUID, credentials: dict) -> None:
        encrypted = self.cipher.encrypt(json.dumps(credentials).encode())
        await db.execute(
            update(Tool).where(
                Tool.id == tool_id,
                Tool.workspace_id == workspace_id,
            ).values(credentials=encrypted.decode())
        )
        await db.commit()

    async def retrieve(self, db: AsyncSession, workspace_id: UUID, tool_id: UUID) -> dict:
        tool = await db.execute(
            select(Tool).where(Tool.id == tool_id, Tool.workspace_id == workspace_id)
        )
        tool = tool.scalar_one()
        return json.loads(self.cipher.decrypt(tool.credentials.encode()))
```

### Step 6: Retrofit Auth into Existing Routes

Update all existing routers to use `Depends(get_current_user)`:

**File**: `backend/app/api/v1/agents.py` (modify)

```python
from app.core.auth import get_current_user

@router.post("/")
async def create_agent(
    data: AgentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Use user's active workspace instead of DEV_WORKSPACE_ID
    workspace_id = user.active_workspace_id
    return await agent_service.create(db, workspace_id, data)
```

Apply the same pattern to: `conversations.py`, `tools.py`, `sandbox.py`.

### Step 7: Frontend — Login/Register Pages

**File**: `frontend/src/app/login/page.tsx`
**File**: `frontend/src/app/register/page.tsx`
**File**: `frontend/src/lib/auth.ts` — token storage, refresh, API client with auth headers

### Step 8: Seed Initial User/Workspace (Development)

Migration seed data for smooth dev transition:

```python
# Create a dev user matching the old DEV_USER_ID
dev_user = User(
    id=UUID(DEV_USER_ID),
    email="dev@yoagent.local",
    password_hash=hash_password("devpassword"),
    display_name="Dev User",
)
dev_workspace = Workspace(
    id=UUID(DEV_WORKSPACE_ID),
    name="Dev Workspace",
    slug="dev",
    owner_id=UUID(DEV_USER_ID),
)
```

---

## Integration Points

- **All prior phases**: Every API endpoint gets auth middleware via `Depends(get_current_user)`
- **Phase 04**: Credential Manager encrypts tool credentials
- **Phase 02**: `workspace_id` and `user_id` columns gain FK constraints
- **Phase 03**: Frontend adds auth headers to all API calls + CopilotKit runtime URL

---

## Verification Checklist

- [ ] `POST /api/v1/auth/register` — creates user, returns tokens
- [ ] `POST /api/v1/auth/login` — returns JWT + refresh token
- [ ] `GET /api/v1/auth/me` with valid JWT — returns user profile
- [ ] All agent/tool/conversation endpoints return 401 without token
- [ ] JWT expiration → 401 → refresh token → new access token
- [ ] API key `ya_sk_...` authenticates successfully via `X-API-Key` header
- [ ] User A cannot access User B's workspace data (tenant isolation)
- [ ] RBAC: viewer cannot create agents, member can, admin can invite
- [ ] GitHub OAuth: redirect → callback → user created → tokens returned
- [ ] Credential Manager: store/retrieve tool credentials (encrypted at rest)
- [ ] Dev seed data: old dev user/workspace exist, no data migration needed

---

## Forward-Looking Notes

- **Phase 09** will add plan-based rate limiting (Free: 60 req/min, Pro: 300 req/min).
- SSO (SAML 2.0 / OIDC) is enterprise-only and deferred.
- Consider adding email verification for production.
- API key scopes should be enforced at the endpoint level — currently just stored.
