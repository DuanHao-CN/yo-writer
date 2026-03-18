# Phase 03: Agent Chat UI — CopilotKit & Streaming

## Meta

| Field | Value |
|-------|-------|
| **Goal** | Streaming chat interface with CopilotKit + AG-UI protocol, visual demo of agent conversation |
| **Prerequisites** | Phase 02 (agent CRUD, ReAct graph, AgentRuntime) |
| **Effort** | 2-3 days |
| **Key Technologies** | CopilotKit, AG-UI Protocol, Next.js App Router, LangGraph streaming |

---

## Context

This phase connects the LangGraph agent (from Phase 02) to a browser-based chat UI using CopilotKit and the AG-UI protocol. The AG-UI protocol is CopilotKit's standardized Agent-UI interaction protocol — it handles LangGraph state synchronization, streaming tokens, and tool call events out of the box (ADR-001).

After this phase, you can open a browser, select an agent, and have a streaming conversation with it. This is the first visual demo milestone.

### AG-UI Protocol Flow

```
User message → CopilotKit (AG-UI Protocol)
             → FastAPI AG-UI Endpoint
             → LangGraph StateGraph.invoke()
                ├── LLM Node → LLM Provider
                └── Tool Node → Mock tools (Phase 02)
             → Streaming response (SSE)
             → CopilotKit renders
```

---

## Data Models

No new tables. This phase uses the agents, conversations, and messages tables from Phase 02.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/agui/{agent_slug}/runs` | AG-UI streaming endpoint (CopilotKit connects here) |

This endpoint is auto-registered by `add_langgraph_fastapi_endpoint`. CopilotKit's frontend SDK sends requests here following the AG-UI protocol.

---

## Implementation Steps

### Step 1: Backend — AG-UI Endpoint

**File**: `backend/app/api/agui.py`

```python
from copilotkit import LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint
from app.runtime.engine import AgentRuntime

def register_agui_endpoints(app, runtime: AgentRuntime):
    """Register AG-UI endpoints for all compiled agent graphs."""
    for slug, compiled_graph in runtime.agents.items():
        add_langgraph_fastapi_endpoint(
            app=app,
            agent=LangGraphAGUIAgent(
                name=slug,
                description=f"Agent: {slug}",
                graph=compiled_graph,
            ),
            path=f"/agui/{slug}",
        )
```

**Dependencies to add** to `backend/pyproject.toml`:

```toml
"copilotkit>=0.1",
"ag-ui-langgraph>=0.1",
"langchain-openai>=0.2",
```

### Step 2: Backend — Startup Registration

**File**: `backend/app/main.py` (modify)

```python
from contextlib import asynccontextmanager
from app.runtime.engine import AgentRuntime
from app.api.agui import register_agui_endpoints

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup: load agents from DB and register AG-UI endpoints
    runtime = AgentRuntime(app)
    app.state.runtime = runtime

    async with async_session() as db:
        agents = await agent_service.list_all(db, DEV_WORKSPACE_ID)
        for agent in agents:
            await runtime.register_agent(agent.config | {"slug": agent.slug})
    register_agui_endpoints(app, runtime)

    yield

app = FastAPI(title="YoAgent API", version=settings.VERSION, lifespan=lifespan)
```

### Step 3: Frontend — Install CopilotKit

```bash
cd frontend
npm install @copilotkit/react-core @copilotkit/react-ui
```

### Step 4: Frontend — Agent List (Dashboard)

**File**: `frontend/src/app/agents/page.tsx`

```tsx
"use client";
import { useEffect, useState } from "react";

interface Agent {
  id: string;
  name: string;
  slug: string;
  description: string;
  status: string;
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/agents`)
      .then(r => r.json())
      .then(setAgents);
  }, []);

  return (
    <div>
      <h1>Agents</h1>
      <ul>
        {agents.map(agent => (
          <li key={agent.id}>
            <a href={`/chat/${agent.slug}`}>{agent.name}</a>
            <p>{agent.description}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### Step 5: Frontend — Chat Layout with CopilotKit Provider

**File**: `frontend/src/app/chat/[agent_slug]/layout.tsx`

```tsx
import { CopilotKit } from "@copilotkit/react-core";

export default function ChatLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { agent_slug: string };
}) {
  return (
    <CopilotKit
      runtimeUrl={`${process.env.NEXT_PUBLIC_API_URL}/agui/${params.agent_slug}`}
      agent={params.agent_slug}
    >
      {children}
    </CopilotKit>
  );
}
```

### Step 6: Frontend — Chat Page

**File**: `frontend/src/app/chat/[agent_slug]/page.tsx`

```tsx
"use client";
import { CopilotChat } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

export default function ChatPage() {
  return (
    <div style={{ height: "100vh" }}>
      <CopilotChat
        labels={{
          title: "AI Agent",
          initial: "How can I help you today?",
        }}
      />
    </div>
  );
}
```

### Step 7: Frontend — Generative UI Actions

**File**: `frontend/src/components/copilot/AgentChat.tsx`

```tsx
"use client";
import { CopilotChat } from "@copilotkit/react-ui";
import { useCopilotAction } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";

export function AgentChat() {
  useCopilotAction({
    name: "render_chart",
    description: "Render a chart from data",
    parameters: [
      { name: "type", type: "string", enum: ["bar", "line", "pie"] },
      { name: "data", type: "object" },
      { name: "title", type: "string" },
    ],
    render: ({ args }) => (
      <div style={{ border: "1px solid #ccc", padding: 16, borderRadius: 8 }}>
        <h3>{args.title}</h3>
        <pre>{JSON.stringify(args.data, null, 2)}</pre>
        <p>Chart type: {args.type}</p>
      </div>
    ),
  });

  useCopilotAction({
    name: "show_code_result",
    description: "Display code execution result with output and artifacts",
    parameters: [
      { name: "code", type: "string" },
      { name: "output", type: "string" },
      { name: "artifacts", type: "object[]" },
    ],
    render: ({ args }) => (
      <div style={{ border: "1px solid #ccc", padding: 16, borderRadius: 8 }}>
        <pre style={{ background: "#f5f5f5", padding: 12 }}>{args.code}</pre>
        <h4>Output</h4>
        <pre>{args.output}</pre>
      </div>
    ),
  });

  return (
    <CopilotChat
      instructions="You are a helpful AI assistant."
      labels={{
        title: "AI Agent",
        initial: "How can I help you today?",
      }}
    />
  );
}
```

### Step 8: Environment Configuration

**File**: `frontend/.env.local`

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Integration Points

- **Phase 02**: Uses `AgentRuntime` and compiled LangGraph graphs
- **Phase 02**: Reads agents from database on startup to register AG-UI endpoints
- Backend must have CORS configured for the frontend origin

Add CORS middleware to `backend/app/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Verification Checklist

- [ ] Backend starts with AG-UI endpoints registered for existing agents
- [ ] `http://localhost:3000/agents` — shows agent list from API
- [ ] `http://localhost:3000/chat/{agent_slug}` — CopilotChat renders
- [ ] Type a message → streaming tokens appear in real time
- [ ] Conversation persists across page reload (checkpointer stores state)
- [ ] `render_chart` and `show_code_result` Generative UI actions render in chat
- [ ] Creating a new agent via API and restarting backend → new agent available in chat

---

## Forward-Looking Notes

- **Phase 04** will make tool calls visible in the chat UI — currently mock tools just return text.
- **Phase 06** will add HITL components (`HITLApproval`, `HITLEditForm`, `HITLReview`) that render inline in the chat using `useCopilotAction` and `useHumanInTheLoop`.
- Consider adding a "create agent" page (`/agents/new`) in a later iteration — for now, agents are created via the API.
- Dynamic agent registration (create agent → immediately available in chat without restart) can be deferred — restart is acceptable for early phases.
