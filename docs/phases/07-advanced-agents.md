# Phase 07: Advanced Agents — Plan-Execute & Multi-Agent

## Meta

| Field | Value |
|-------|-------|
| **Goal** | Plan-Execute graph with HITL plan approval, Multi-Agent supervisor, agent versioning |
| **Prerequisites** | Phase 05 (sandbox), Phase 06 (HITL patterns) |
| **Effort** | 3-4 days |
| **Key Technologies** | LangGraph StateGraph, interrupt(), Multi-Agent supervisor pattern |

---

## Context

This phase adds two advanced agent orchestration patterns beyond the basic ReAct agent:

1. **Plan-Execute Agent** — LLM generates a multi-step plan, user approves/edits the plan via HITL, then steps execute sequentially. Ideal for complex multi-step tasks.

2. **Multi-Agent Supervisor** — A supervisor agent routes tasks to specialized sub-agents (researcher, coder, reviewer). HITL interrupt before delegation for transparency.

Both patterns integrate with the HITL system from Phase 06 for human oversight.

This phase also implements **agent versioning** — snapshoting agent config on updates and supporting rollback. The `agent_versions` table was created in Phase 02 but the logic is implemented here.

### Plan-Execute Flow

```
User message → Planner LLM → [Step 1, Step 2, Step 3]
                                    │
                              interrupt() ← User approves/edits plan
                                    │
                              Execute Step 1 → Result 1
                              Execute Step 2 → Result 2
                              Execute Step 3 → Result 3
                                    │
                              Synthesizer → Final answer
```

### Multi-Agent Flow

```
User message → Supervisor LLM → "delegate to researcher"
                                    │
                              interrupt() ← User approves routing
                                    │
                              Researcher Agent → Research result
                                    │
                              Supervisor LLM → "delegate to coder"
                                    │
                              Coder Agent → Code result
                                    │
                              Supervisor LLM → "done"
                                    │
                              Final answer
```

---

## Data Models

No new tables. Uses:
- `agent_versions` (created Phase 02) — for versioning logic
- Checkpointer — for HITL interrupt state

---

## API Endpoints

### Agent Versioning

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/agents/{agent_id}/versions` | List all versions |
| GET | `/api/v1/agents/{agent_id}/versions/{version}` | Get specific version config |
| POST | `/api/v1/agents/{agent_id}/rollback/{version}` | Rollback to a specific version |

**Version Response**:

```json
{
  "id": "uuid",
  "agent_id": "uuid",
  "version": 3,
  "config": { "...agent config snapshot..." },
  "changelog": "Updated system prompt for better code generation",
  "created_at": "2026-03-17T10:00:00Z"
}
```

---

## Implementation Steps

### Step 1: Plan-Execute Graph

**File**: `backend/app/runtime/graphs/plan_execute.py`

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.types import interrupt, Command
from langchain_core.messages import AIMessage

class PlanExecuteState(TypedDict):
    messages: Annotated[list, add_messages]
    agent_config: dict
    plan: list[str]
    current_step: int
    step_results: list[str]
    final_answer: str

async def planner_node(state: PlanExecuteState):
    """LLM analyzes user request and generates execution plan."""
    model = get_model_for_agent(state["agent_config"])
    user_message = state["messages"][-1].content
    response = await model.ainvoke(
        f"Break down this task into concrete steps. "
        f"Return a numbered list of steps.\n\nTask: {user_message}"
    )
    plan = parse_plan(response.content)
    return {"plan": plan, "current_step": 0, "step_results": []}

async def plan_approval_node(state: PlanExecuteState):
    """HITL: Let user approve, edit, or reorder the plan before execution."""
    decision = interrupt({
        "type": "plan_approval",
        "plan": state["plan"],
        "message": "Review the execution plan. You can approve, edit steps, or reorder.",
    })

    action = decision.get("action", "approve")
    if action == "approve":
        return {}
    elif action == "edit":
        return {"plan": decision["edited_plan"]}
    elif action == "reject":
        return {
            "plan": [],
            "final_answer": "Plan was rejected by user.",
            "messages": [AIMessage(content="Plan was rejected. Let me know if you'd like to try a different approach.")]
        }
    return {}

async def executor_node(state: PlanExecuteState):
    """Execute current step using LLM + tools."""
    step = state["plan"][state["current_step"]]
    model = get_model_for_agent(state["agent_config"])

    # Execute step with available tools
    result = await model.ainvoke(
        f"Execute this step: {step}\n\n"
        f"Previous results: {state['step_results']}"
    )
    return {
        "step_results": [*state["step_results"], result.content],
        "current_step": state["current_step"] + 1,
    }

async def synthesizer_node(state: PlanExecuteState):
    """Combine all step results into a final answer."""
    model = get_model_for_agent(state["agent_config"])
    response = await model.ainvoke(
        f"Synthesize these results into a comprehensive answer:\n\n"
        f"Plan: {state['plan']}\n\n"
        f"Results: {state['step_results']}"
    )
    return {
        "final_answer": response.content,
        "messages": [AIMessage(content=response.content)],
    }

def route_after_approval(state: PlanExecuteState):
    if not state["plan"]:
        return END
    return "execute"

def route_after_execute(state: PlanExecuteState):
    if state["current_step"] >= len(state["plan"]):
        return "synthesize"
    return "execute"

def build_plan_execute_graph() -> StateGraph:
    graph = StateGraph(PlanExecuteState)
    graph.add_node("plan", planner_node)
    graph.add_node("approve_plan", plan_approval_node)
    graph.add_node("execute", executor_node)
    graph.add_node("synthesize", synthesizer_node)

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "approve_plan")
    graph.add_conditional_edges("approve_plan", route_after_approval, ["execute", END])
    graph.add_conditional_edges("execute", route_after_execute, ["execute", "synthesize"])
    graph.add_edge("synthesize", END)

    return graph
```

### Step 2: Multi-Agent Supervisor Graph

**File**: `backend/app/runtime/graphs/multi_agent.py`

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.types import interrupt

class SupervisorState(TypedDict):
    messages: Annotated[list, add_messages]
    agent_config: dict
    next_agent: str
    agent_outputs: dict[str, str]

async def supervisor_node(state: SupervisorState):
    """Supervisor LLM decides which sub-agent to delegate to."""
    model = get_model_for_agent(state["agent_config"])
    response = await model.ainvoke(
        f"You are a supervisor coordinating these agents: researcher, coder, reviewer.\n"
        f"Current state: {state}\n"
        f"Decide which agent should act next, or 'done' if the task is complete.\n"
        f"Respond with just the agent name."
    )
    next_agent = response.content.strip().lower()
    return {"next_agent": next_agent}

async def delegation_approval_node(state: SupervisorState):
    """HITL: Let user approve routing decision."""
    decision = interrupt({
        "type": "delegation_approval",
        "next_agent": state["next_agent"],
        "message": f"Supervisor wants to delegate to '{state['next_agent']}'. Approve?",
        "available_agents": ["researcher", "coder", "reviewer"],
    })

    action = decision.get("action", "approve")
    if action == "approve":
        return {}
    elif action == "redirect":
        return {"next_agent": decision["target_agent"]}
    elif action == "done":
        return {"next_agent": "done"}
    return {}

async def researcher_node(state: SupervisorState):
    """Researcher sub-agent: information retrieval."""
    model = get_model_for_agent(state["agent_config"])
    result = await model.ainvoke(
        f"As a researcher, find relevant information for: {state['messages'][-1].content}\n"
        f"Previous outputs: {state['agent_outputs']}"
    )
    return {"agent_outputs": {**state["agent_outputs"], "researcher": result.content}}

async def coder_node(state: SupervisorState):
    """Coder sub-agent: code generation and execution."""
    model = get_model_for_agent(state["agent_config"])
    result = await model.ainvoke(
        f"As a coder, write code for: {state['messages'][-1].content}\n"
        f"Previous outputs: {state['agent_outputs']}"
    )
    return {"agent_outputs": {**state["agent_outputs"], "coder": result.content}}

async def reviewer_node(state: SupervisorState):
    """Reviewer sub-agent: quality review."""
    model = get_model_for_agent(state["agent_config"])
    result = await model.ainvoke(
        f"As a reviewer, review the work done so far:\n"
        f"Outputs: {state['agent_outputs']}"
    )
    return {"agent_outputs": {**state["agent_outputs"], "reviewer": result.content}}

def route_delegation(state: SupervisorState):
    return state["next_agent"]

def build_multi_agent_graph() -> StateGraph:
    graph = StateGraph(SupervisorState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("approve_delegation", delegation_approval_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("coder", coder_node)
    graph.add_node("reviewer", reviewer_node)

    graph.add_edge(START, "supervisor")
    graph.add_edge("supervisor", "approve_delegation")
    graph.add_conditional_edges("approve_delegation", route_delegation, {
        "researcher": "researcher",
        "coder": "coder",
        "reviewer": "reviewer",
        "done": END,
    })
    for agent in ["researcher", "coder", "reviewer"]:
        graph.add_edge(agent, "supervisor")

    return graph
```

### Step 3: Update AgentRuntime Graph Builder

**File**: `backend/app/runtime/engine.py` (modify `_build_graph`)

```python
from app.runtime.graphs.plan_execute import build_plan_execute_graph
from app.runtime.graphs.multi_agent import build_multi_agent_graph

def _build_graph(self, config: dict) -> StateGraph:
    graph_type = config.get("graph", {}).get("type", "react")

    if graph_type == "react":
        # ... existing react/react_hitl logic from Phase 06
        pass
    elif graph_type == "plan-execute":
        return build_plan_execute_graph()
    elif graph_type == "multi-agent":
        return build_multi_agent_graph()
    else:
        raise ValueError(f"Unknown graph type: {graph_type}")
```

### Step 4: Frontend — Plan Approval Component

**File**: `frontend/src/components/hitl/PlanApproval.tsx`

```tsx
"use client";
import { useState } from "react";

interface PlanApprovalProps {
  plan: string[];
  message: string;
  onApprove: () => void;
  onEdit: (editedPlan: string[]) => void;
  onReject: () => void;
}

export function PlanApproval({ plan, message, onApprove, onEdit, onReject }: PlanApprovalProps) {
  const [steps, setSteps] = useState(plan);

  const moveStep = (index: number, direction: "up" | "down") => {
    const newSteps = [...steps];
    const target = direction === "up" ? index - 1 : index + 1;
    if (target < 0 || target >= newSteps.length) return;
    [newSteps[index], newSteps[target]] = [newSteps[target], newSteps[index]];
    setSteps(newSteps);
  };

  const removeStep = (index: number) => {
    setSteps(steps.filter((_, i) => i !== index));
  };

  const editStep = (index: number, value: string) => {
    const newSteps = [...steps];
    newSteps[index] = value;
    setSteps(newSteps);
  };

  return (
    <div style={{
      border: "2px solid #f59e0b",
      borderRadius: 8,
      padding: 16,
      margin: "8px 0",
      backgroundColor: "#fffbeb",
    }}>
      <h4 style={{ margin: "0 0 8px" }}>Execution Plan</h4>
      <p>{message}</p>
      <ol style={{ paddingLeft: 20 }}>
        {steps.map((step, i) => (
          <li key={i} style={{ marginBottom: 8, display: "flex", alignItems: "center", gap: 8 }}>
            <input
              value={step}
              onChange={(e) => editStep(i, e.target.value)}
              style={{ flex: 1, padding: 4, border: "1px solid #ccc", borderRadius: 4 }}
            />
            <button onClick={() => moveStep(i, "up")} disabled={i === 0}>↑</button>
            <button onClick={() => moveStep(i, "down")} disabled={i === steps.length - 1}>↓</button>
            <button onClick={() => removeStep(i)} style={{ color: "red" }}>×</button>
          </li>
        ))}
      </ol>
      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={onApprove} style={{ padding: "8px 16px", background: "#22c55e", color: "white", border: "none", borderRadius: 4 }}>
          Approve Plan
        </button>
        <button onClick={() => onEdit(steps)} style={{ padding: "8px 16px", background: "#3b82f6", color: "white", border: "none", borderRadius: 4 }}>
          Approve Edited Plan
        </button>
        <button onClick={onReject} style={{ padding: "8px 16px", background: "#ef4444", color: "white", border: "none", borderRadius: 4 }}>
          Reject
        </button>
      </div>
    </div>
  );
}
```

### Step 5: Frontend — Agent Delegation Component

**File**: `frontend/src/components/hitl/AgentDelegation.tsx`

```tsx
"use client";

interface AgentDelegationProps {
  nextAgent: string;
  availableAgents: string[];
  message: string;
  onApprove: () => void;
  onRedirect: (agent: string) => void;
  onDone: () => void;
}

export function AgentDelegation({
  nextAgent,
  availableAgents,
  message,
  onApprove,
  onRedirect,
  onDone,
}: AgentDelegationProps) {
  return (
    <div style={{
      border: "2px solid #8b5cf6",
      borderRadius: 8,
      padding: 16,
      margin: "8px 0",
      backgroundColor: "#f5f3ff",
    }}>
      <h4 style={{ margin: "0 0 8px" }}>Delegation Decision</h4>
      <p>{message}</p>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button onClick={onApprove} style={{ padding: "8px 16px", background: "#22c55e", color: "white", border: "none", borderRadius: 4 }}>
          Approve → {nextAgent}
        </button>
        {availableAgents.filter(a => a !== nextAgent).map(agent => (
          <button key={agent} onClick={() => onRedirect(agent)} style={{ padding: "8px 16px", background: "#3b82f6", color: "white", border: "none", borderRadius: 4 }}>
            Redirect → {agent}
          </button>
        ))}
        <button onClick={onDone} style={{ padding: "8px 16px", background: "#ef4444", color: "white", border: "none", borderRadius: 4 }}>
          Stop (Done)
        </button>
      </div>
    </div>
  );
}
```

### Step 6: Register HITL actions for Plan & Delegation

Add `useCopilotAction` registrations for `hitl_plan_approval` and `hitl_delegation_approval` in `AgentChat.tsx`.

### Step 7: Agent Versioning Logic

**File**: `backend/app/services/agent_service.py` (extend)

```python
async def update_agent(db: AsyncSession, agent_id: UUID, data: AgentUpdate) -> Agent:
    agent = await get(db, agent_id)

    # Snapshot current config as a new version
    version = AgentVersion(
        agent_id=agent.id,
        version=agent.current_version,
        config=agent.config,
        changelog=data.changelog or "Updated",
        created_by=UUID(DEV_USER_ID),
    )
    db.add(version)

    # Apply updates
    for field, value in data.dict(exclude_unset=True).items():
        setattr(agent, field, value)
    agent.current_version += 1
    await db.commit()
    return agent

async def rollback_agent(db: AsyncSession, agent_id: UUID, target_version: int) -> Agent:
    version = await db.execute(
        select(AgentVersion).where(
            AgentVersion.agent_id == agent_id,
            AgentVersion.version == target_version,
        )
    )
    version = version.scalar_one()
    agent = await get(db, agent_id)
    agent.config = version.config
    agent.current_version += 1

    # Record rollback as new version
    rollback_version = AgentVersion(
        agent_id=agent.id,
        version=agent.current_version,
        config=version.config,
        changelog=f"Rollback to version {target_version}",
        created_by=UUID(DEV_USER_ID),
    )
    db.add(rollback_version)
    await db.commit()
    return agent
```

### Step 8: Versioning API Routes

**File**: `backend/app/api/v1/agents.py` (extend)

```python
@router.get("/{agent_id}/versions")
async def list_versions(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    return await agent_service.list_versions(db, agent_id)

@router.get("/{agent_id}/versions/{version}")
async def get_version(agent_id: UUID, version: int, db: AsyncSession = Depends(get_db)):
    return await agent_service.get_version(db, agent_id, version)

@router.post("/{agent_id}/rollback/{version}")
async def rollback(agent_id: UUID, version: int, db: AsyncSession = Depends(get_db)):
    return await agent_service.rollback_agent(db, agent_id, version)
```

---

## Integration Points

- **Phase 06**: Plan-Execute uses `interrupt()` for plan approval. Multi-Agent uses `interrupt()` for delegation approval.
- **Phase 05**: Executor node can use code_sandbox tool for code-related steps.
- **Phase 04**: All tool calls route through MCP gateway.
- **Phase 02**: Agent versioning uses `agent_versions` table created in Phase 02.

---

## Verification Checklist

- [ ] Create Plan-Execute agent with `config.graph.type: "plan-execute"`
- [ ] Send task → plan generated → plan approval dialog appears
- [ ] Approve plan → steps execute sequentially → synthesized answer
- [ ] Edit plan (reorder/remove steps) → modified plan executes
- [ ] Reject plan → agent acknowledges, no execution
- [ ] Create Multi-Agent with `config.graph.type: "multi-agent"`
- [ ] Send task → supervisor decides agent → delegation dialog appears
- [ ] Approve delegation → sub-agent executes → returns to supervisor
- [ ] Redirect to different agent → that agent executes instead
- [ ] Agent versioning: PATCH agent → version snapshot created
- [ ] `GET /agents/{id}/versions` → lists version history
- [ ] `POST /agents/{id}/rollback/1` → config reverts to version 1

---

## Forward-Looking Notes

- **Phase 08** will add `created_by` FK to `agent_versions` referencing the `users` table.
- Sub-agents in Multi-Agent can themselves be full agents with their own tool bindings — this is an extension point.
- Plan-Execute can be enhanced with step-level HITL approval (interrupt before each step, not just the full plan).
- Consider adding a graph visualization endpoint that returns the StateGraph as a DOT or JSON format for frontend rendering.
