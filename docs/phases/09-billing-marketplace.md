# Phase 09: Billing & Tool Marketplace

## Meta

| Field | Value |
|-------|-------|
| **Goal** | Usage metering, Stripe billing, plan-based rate limiting, tool marketplace |
| **Prerequisites** | Phase 08 (auth, users, workspaces) |
| **Effort** | 3-4 days |
| **Key Technologies** | Stripe, FastAPI middleware, Redis rate limiting |

---

## Context

This phase adds monetization and ecosystem features:

1. **Usage Metering** — Track token consumption, tool calls, sandbox CPU by workspace
2. **Stripe Integration** — Subscription management with Free/Pro/Team plans
3. **Rate Limiting** — Plan-based request and resource limits
4. **Tool Marketplace** — Browse, install, and publish community MCP tools

### Pricing Plans

| Plan | Price | Includes |
|------|-------|----------|
| **Free** | $0/mo | 50K tokens, 100 tool calls, 10 min sandbox |
| **Pro** | $29/mo | 2M tokens, 5K tool calls, 2h sandbox, 5 Agents |
| **Team** | $99/mo/seat | 10M tokens, 50K tool calls, 10h sandbox, unlimited Agents |
| **Enterprise** | Custom | Private deploy, SSO, SLA, audit logs |

### Rate Limits

| Plan | API Requests | Concurrent Agents |
|------|-------------|-------------------|
| Free | 60 req/min | 1 |
| Pro | 300 req/min | 5 |
| Team | 1000 req/min | 20 |

---

## Data Models

### Alembic Migration

```sql
-- Usage Records
CREATE TABLE usage_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    type            VARCHAR(30) NOT NULL,  -- llm_tokens | tool_calls | sandbox_cpu | storage
    quantity        BIGINT NOT NULL,
    unit            VARCHAR(20),           -- tokens | calls | seconds | bytes
    metadata        JSONB DEFAULT '{}',    -- {model, agent_id, tool_name, etc.}
    recorded_at     TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_usage_workspace_time ON usage_records(workspace_id, recorded_at);
CREATE INDEX idx_usage_workspace_type ON usage_records(workspace_id, type, recorded_at);

-- Marketplace Tools
CREATE TABLE marketplace_tools (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    publisher_id    UUID REFERENCES users(id),
    name            VARCHAR(100) NOT NULL,
    slug            VARCHAR(100) UNIQUE NOT NULL,
    description     TEXT,
    long_description TEXT,
    icon_url        TEXT,
    category        VARCHAR(50),           -- database | communication | dev-tools | ...
    tags            TEXT[],
    mcp_endpoint    TEXT NOT NULL,          -- MCP Server address
    auth_type       VARCHAR(20),           -- none | api_key | oauth2
    auth_config     JSONB,                 -- OAuth scopes, key format, etc.
    schema_json     JSONB,                 -- tool list and schemas
    install_count   INT DEFAULT 0,
    rating_avg      DECIMAL(2,1) DEFAULT 0,
    rating_count    INT DEFAULT 0,
    status          VARCHAR(20) DEFAULT 'pending',  -- pending | approved | rejected
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## API Endpoints

### Usage & Billing

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/usage` | Get workspace usage summary (current period) |
| GET | `/api/v1/usage/history` | Usage history with date range |
| GET | `/api/v1/billing/plan` | Get current plan details |
| POST | `/api/v1/billing/checkout` | Create Stripe checkout session |
| POST | `/api/v1/billing/portal` | Create Stripe customer portal link |
| POST | `/api/v1/billing/webhook` | Stripe webhook handler |

**Usage Response**:

```json
{
  "period": {"start": "2026-03-01", "end": "2026-03-31"},
  "usage": {
    "llm_tokens": {"used": 125000, "limit": 2000000, "unit": "tokens"},
    "tool_calls": {"used": 850, "limit": 5000, "unit": "calls"},
    "sandbox_cpu": {"used": 1200, "limit": 7200, "unit": "seconds"},
    "storage": {"used": 52428800, "limit": 1073741824, "unit": "bytes"}
  },
  "plan": "pro"
}
```

### Tool Marketplace

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/marketplace/tools` | Browse marketplace (supports search, category filter) |
| GET | `/api/v1/marketplace/tools/{slug}` | Get marketplace tool details |
| POST | `/api/v1/marketplace/tools/{slug}/install` | Install tool to workspace |
| POST | `/api/v1/marketplace/tools` | Publish tool to marketplace |

**Browse Marketplace**:

```
GET /api/v1/marketplace/tools?category=database&search=postgres&sort=popular
```

**Response**:

```json
{
  "tools": [
    {
      "slug": "postgres-connector",
      "name": "PostgreSQL Connector",
      "description": "Query PostgreSQL databases",
      "category": "database",
      "install_count": 1250,
      "rating_avg": 4.5,
      "auth_type": "api_key"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

**Install Tool**:

```json
POST /api/v1/marketplace/tools/postgres-connector/install
{
  "credentials": {
    "host": "db.example.com",
    "password": "***"
  }
}
```

---

## Implementation Steps

### Step 1: Usage Metering Middleware

**File**: `backend/app/middleware/usage.py`

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class UsageMeteringMiddleware(BaseHTTPMiddleware):
    """Record usage metrics for billing."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Record API request count (for rate limiting)
        if hasattr(request.state, "user"):
            await record_api_request(request.state.user.workspace_id)

        return response
```

### Step 2: Usage Service

**File**: `backend/app/services/usage_service.py`

```python
async def record_usage(
    db: AsyncSession,
    workspace_id: UUID,
    usage_type: str,
    quantity: int,
    unit: str,
    metadata: dict | None = None,
):
    record = UsageRecord(
        workspace_id=workspace_id,
        type=usage_type,
        quantity=quantity,
        unit=unit,
        metadata=metadata or {},
    )
    db.add(record)
    await db.commit()

async def get_usage_summary(
    db: AsyncSession,
    workspace_id: UUID,
    period_start: datetime,
    period_end: datetime,
) -> dict:
    """Aggregate usage by type for billing period."""
    result = await db.execute(
        select(
            UsageRecord.type,
            func.sum(UsageRecord.quantity).label("total"),
        ).where(
            UsageRecord.workspace_id == workspace_id,
            UsageRecord.recorded_at >= period_start,
            UsageRecord.recorded_at < period_end,
        ).group_by(UsageRecord.type)
    )
    return {row.type: row.total for row in result.all()}

PLAN_LIMITS = {
    "free": {
        "llm_tokens": 50_000,
        "tool_calls": 100,
        "sandbox_cpu": 600,      # 10 minutes in seconds
        "agents": 2,
        "rate_limit": 60,        # requests per minute
    },
    "pro": {
        "llm_tokens": 2_000_000,
        "tool_calls": 5_000,
        "sandbox_cpu": 7_200,    # 2 hours
        "agents": 5,
        "rate_limit": 300,
    },
    "team": {
        "llm_tokens": 10_000_000,
        "tool_calls": 50_000,
        "sandbox_cpu": 36_000,   # 10 hours
        "agents": -1,            # unlimited
        "rate_limit": 1000,
    },
}

async def check_quota(db: AsyncSession, workspace_id: UUID, usage_type: str, plan: str) -> bool:
    """Check if workspace is within quota for usage type."""
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    limit = limits.get(usage_type)
    if limit == -1:
        return True
    current = await get_current_period_usage(db, workspace_id, usage_type)
    return current < limit
```

### Step 3: Rate Limiting (Redis)

**File**: `backend/app/middleware/rate_limit.py`

```python
import redis.asyncio as redis
from app.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL)

async def check_rate_limit(workspace_id: str, plan: str) -> bool:
    """Sliding window rate limiter using Redis."""
    limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])["rate_limit"]
    key = f"rate_limit:{workspace_id}"

    pipe = redis_client.pipeline()
    now = time.time()
    window = 60  # 1 minute

    pipe.zremrangebyscore(key, 0, now - window)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, window)
    results = await pipe.execute()

    count = results[2]
    return count <= limit
```

### Step 4: Integrate Usage Recording into Agent Runtime

**File**: `backend/app/runtime/graphs/react.py` (modify `llm_node`)

After LLM call, record token usage:

```python
async def llm_node(state: MessagesState):
    # ... existing LLM call ...
    response = await model_with_tools.ainvoke(...)

    # Record token usage
    if hasattr(response, "usage_metadata"):
        await record_usage(
            db, workspace_id, "llm_tokens",
            response.usage_metadata.get("total_tokens", 0),
            "tokens",
            {"model": state["agent_config"]["model"]["model_id"]},
        )

    return {"messages": [response]}
```

Similarly, record `tool_calls` usage in `tool_node` and `sandbox_cpu` in sandbox execution.

### Step 5: Stripe Integration

**File**: `backend/app/services/billing_service.py`

```python
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

async def create_checkout_session(workspace_id: UUID, plan: str, user_email: str) -> str:
    """Create Stripe Checkout session for plan upgrade."""
    price_ids = {
        "pro": settings.STRIPE_PRO_PRICE_ID,
        "team": settings.STRIPE_TEAM_PRICE_ID,
    }
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_ids[plan], "quantity": 1}],
        customer_email=user_email,
        success_url=f"{settings.FRONTEND_URL}/settings/billing?success=true",
        cancel_url=f"{settings.FRONTEND_URL}/settings/billing?canceled=true",
        metadata={"workspace_id": str(workspace_id)},
    )
    return session.url

async def handle_webhook(payload: bytes, sig_header: str) -> None:
    """Process Stripe webhook events (idempotent).

    Stripe may retry webhooks up to ~15 times over 72h.
    Use event.id as idempotency key to prevent double-processing.
    """
    event = stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )

    # Idempotency check: skip already-processed events
    if await is_event_processed(event["id"]):
        return

    try:
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            workspace_id = session["metadata"]["workspace_id"]
            await update_workspace_plan(workspace_id, plan="pro")

        elif event["type"] == "customer.subscription.deleted":
            await downgrade_to_free(event)

        # Mark event as processed
        await mark_event_processed(event["id"])
    except Exception:
        # Don't mark as processed — Stripe will retry
        raise
```

**Idempotency**: Store processed event IDs in Redis with 72h TTL (matches Stripe retry window):

```python
async def is_event_processed(event_id: str) -> bool:
    return await redis_client.exists(f"stripe_event:{event_id}")

async def mark_event_processed(event_id: str) -> None:
    await redis_client.setex(f"stripe_event:{event_id}", 259200, "1")  # 72h
```

### Step 6: Billing API Routes

**File**: `backend/app/api/v1/billing.py`

### Step 7: Marketplace Service & Routes

**File**: `backend/app/services/marketplace_service.py`

```python
async def install_marketplace_tool(
    db: AsyncSession, workspace_id: UUID, tool_slug: str, credentials: dict
) -> Tool:
    """Install a marketplace tool into a workspace."""
    marketplace_tool = await get_marketplace_tool_by_slug(db, tool_slug)

    # Create workspace-local tool entry
    tool = Tool(
        workspace_id=workspace_id,
        name=marketplace_tool.name,
        slug=f"mp-{marketplace_tool.slug}",
        description=marketplace_tool.description,
        type="marketplace",
        mcp_uri=marketplace_tool.mcp_endpoint,
        schema_json=marketplace_tool.schema_json,
    )
    db.add(tool)

    # Encrypt and store credentials
    if credentials:
        await credential_manager.store(db, workspace_id, tool.id, credentials)

    # Increment install count
    marketplace_tool.install_count += 1
    await db.commit()
    return tool
```

**File**: `backend/app/api/v1/marketplace.py`

### Step 8: Frontend — Usage Dashboard

**File**: `frontend/src/app/settings/usage/page.tsx`

Show usage bars for tokens, tool calls, sandbox time with limits.

### Step 9: Frontend — Marketplace Browse Page

**File**: `frontend/src/app/marketplace/page.tsx`

Grid of marketplace tools with search, category filter, install button.

---

## Integration Points

- **Phase 08**: Uses `users.plan` for rate limiting and quota enforcement
- **Phase 04**: Marketplace tool installation creates entries in `tools` table
- **Phase 04**: Tool call recording feeds into `tool_calls` usage metering
- **Phase 05**: Sandbox execution time feeds into `sandbox_cpu` usage metering
- **Phase 02**: Token consumption from LLM calls feeds into `llm_tokens` metering
- **Phase 08**: Credential Manager encrypts marketplace tool credentials

---

## Verification Checklist

- [ ] `uv run alembic upgrade head` — creates `usage_records` and `marketplace_tools` tables
- [ ] Usage recording: agent run → token usage recorded in `usage_records`
- [ ] Usage recording: tool call → call count recorded
- [ ] Usage recording: sandbox execution → CPU seconds recorded
- [ ] `GET /api/v1/usage` — returns usage summary with limits
- [ ] Free plan: exceeding 50K tokens → 429 error with quota message
- [ ] Rate limiting: Free plan → 61st request in 1 minute → 429
- [ ] `POST /api/v1/billing/checkout` → redirects to Stripe checkout
- [ ] Stripe webhook → plan upgrade → user.plan updated → higher limits
- [ ] `GET /api/v1/marketplace/tools` — returns marketplace tool list
- [ ] `POST /api/v1/marketplace/tools/slack/install` — tool appears in workspace
- [ ] Installed marketplace tool is usable by agents

---

## Forward-Looking Notes

- **Phase 10** will add Grafana dashboards for usage metrics.
- Enterprise billing (custom contracts, invoicing) is deferred.
- Consider adding usage alerts (email when 80% of quota used).
- Marketplace tool review/approval workflow is manual initially — automated scanning can be added later.
- Consider caching usage aggregates in Redis to avoid frequent DB queries.
