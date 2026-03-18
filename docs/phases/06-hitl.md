# Phase 06: Human-in-the-Loop (HITL) Patterns

## Meta

| Field | Value |
|-------|-------|
| **Goal** | Implement 4 HITL patterns: approval, edit, review, form input — with LangGraph interrupt + CopilotKit UI |
| **Prerequisites** | Phase 02 (agent core, ReAct graph), Phase 03 (CopilotKit chat UI) |
| **Effort** | 2-3 days |
| **Key Technologies** | LangGraph `interrupt()` / `Command(resume=...)`, CopilotKit `useHumanInTheLoop` |

---

## Context

Human-in-the-Loop (HITL) lets agents pause execution to get human approval, edits, or input before proceeding. This is critical for:

- **Safety**: Approve destructive tool calls before execution
- **Quality**: Edit agent-generated content before sending
- **Control**: Review and modify agent plans before execution
- **Data collection**: Agent requests structured data mid-conversation

### How LangGraph Interrupt Works

LangGraph's `interrupt()` function pauses graph execution and returns a payload to the client. The graph state is persisted via the checkpointer. When the user responds, `Command(resume=value)` resumes execution from the interruption point with the user's input.

```
Agent Graph Execution:
  1. LLM decides to call tool
  2. should_continue → "tools"
  3. tool_node_with_hitl → interrupt(payload)  ← PAUSE
     ... graph state saved to PostgreSQL ...
  4. User approves/edits/rejects in UI
  5. Command(resume=decision) → tool executes or skips  ← RESUME
  6. Continue to LLM node
```

### No New Tables

HITL state is managed entirely by LangGraph's checkpointer (PostgreSQL). The interrupt payload and resume value are stored as part of the graph checkpoint. No additional database tables needed.

---

## Data Models

No new tables. HITL uses the existing checkpointer for interrupt state persistence.

An `hitl_config` field is added to the agent's `config` JSONB:

```json
{
  "config": {
    "hitl": {
      "require_approval": ["web_search", "code_sandbox"],
      "require_review": ["send_email", "post_slack"],
      "form_schemas": {
        "collect_preferences": {
          "type": "object",
          "properties": {
            "language": {"type": "string", "enum": ["en", "zh", "ja"]},
            "detail_level": {"type": "string", "enum": ["brief", "detailed"]}
          }
        }
      }
    }
  }
}
```

---

## API Endpoints

No new REST endpoints. HITL interactions flow through the existing AG-UI protocol:

1. Backend sends interrupt event via AG-UI streaming
2. CopilotKit renders HITL UI component
3. User responds via CopilotKit
4. CopilotKit sends `Command(resume=...)` back through AG-UI

---

## Implementation Steps

### Step 1: HITL-Enhanced Tool Node

**File**: `backend/app/runtime/graphs/react_hitl.py`

```python
from langgraph.types import interrupt, Command
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import ToolMessage
from app.runtime.graphs.react import llm_node, should_continue
from app.runtime.mcp_gateway import gateway

async def tool_node_with_hitl(state: MessagesState):
    """Tool node with HITL interrupt for configured tools.

    Wraps Phase 02/04's tool_node to add approval/edit before execution.
    """
    hitl_config = state.get("agent_config", {}).get("hitl", {})
    require_approval = hitl_config.get("require_approval", [])
    require_review = hitl_config.get("require_review", [])

    results = []
    for tool_call in state["messages"][-1].tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        # Pattern 1: APPROVAL — approve/reject before execution
        if tool_name in require_approval:
            decision = interrupt({
                "type": "approval",
                "tool_name": tool_name,
                "tool_args": tool_args,
                "message": f"Agent wants to call '{tool_name}'. Approve?",
            })

            if decision["action"] == "reject":
                results.append(ToolMessage(
                    content=f"Tool call '{tool_name}' was rejected by user.",
                    tool_call_id=tool_call["id"]
                ))
                continue
            elif decision["action"] == "edit":
                # Pattern 2: EDIT — user modified the arguments
                tool_args = decision.get("edited_args", tool_args)

        # Pattern 3: REVIEW — for tools that produce content to review
        if tool_name in require_review:
            # Execute tool first, then let user review output
            result = await gateway.call_tool(
                tool_name=tool_name,
                arguments=tool_args,
            )
            reviewed = interrupt({
                "type": "review",
                "tool_name": tool_name,
                "original_output": str(result),
                "message": f"Review the output of '{tool_name}' before proceeding.",
            })
            final_output = reviewed.get("edited_output", str(result))
            results.append(ToolMessage(
                content=final_output,
                tool_call_id=tool_call["id"]
            ))
            continue

        # No HITL required — execute normally
        try:
            result = await gateway.call_tool(
                tool_name=tool_name,
                arguments=tool_args,
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


async def form_input_node(state: MessagesState):
    """Pattern 4: FORM INPUT — agent requests structured data from user.

    This node can be inserted into any graph where the agent needs
    structured user input mid-execution.
    """
    form_config = state.get("form_request", {})
    user_input = interrupt({
        "type": "form_input",
        "schema": form_config.get("schema", {}),
        "title": form_config.get("title", "Please provide information"),
        "message": form_config.get("message", ""),
    })
    return {"form_data": user_input}


def build_react_hitl_graph() -> StateGraph:
    """Build ReAct graph with HITL-enhanced tool node."""
    graph = StateGraph(MessagesState)
    graph.add_node("llm", llm_node)
    graph.add_node("tools", tool_node_with_hitl)  # HITL version
    graph.add_edge(START, "llm")
    graph.add_conditional_edges("llm", should_continue, ["tools", END])
    graph.add_edge("tools", "llm")
    return graph
```

### Step 2: Update AgentRuntime to Use HITL Graph

**File**: `backend/app/runtime/engine.py` (modify `_build_graph`)

```python
from app.runtime.graphs.react import build_react_graph
from app.runtime.graphs.react_hitl import build_react_hitl_graph

def _build_graph(self, config: dict) -> StateGraph:
    hitl_config = config.get("hitl", {})
    has_hitl = (
        hitl_config.get("require_approval") or
        hitl_config.get("require_review")
    )

    if config.get("graph", {}).get("type") == "react":
        if has_hitl:
            return build_react_hitl_graph()
        return build_react_graph()
    # ... other graph types
```

### Step 3: Frontend — HITL Approval Component

**File**: `frontend/src/components/hitl/HITLApproval.tsx`

```tsx
"use client";

interface HITLApprovalProps {
  toolName: string;
  toolArgs: Record<string, unknown>;
  message: string;
  onApprove: () => void;
  onReject: () => void;
  onEdit: (editedArgs: Record<string, unknown>) => void;
}

export function HITLApproval({
  toolName,
  toolArgs,
  message,
  onApprove,
  onReject,
  onEdit,
}: HITLApprovalProps) {
  return (
    <div style={{
      border: "2px solid #f59e0b",
      borderRadius: 8,
      padding: 16,
      margin: "8px 0",
      backgroundColor: "#fffbeb",
    }}>
      <h4 style={{ margin: "0 0 8px" }}>Action Required</h4>
      <p>{message}</p>
      <div style={{ background: "#f5f5f5", padding: 12, borderRadius: 4, margin: "8px 0" }}>
        <strong>Tool:</strong> {toolName}
        <pre style={{ margin: "4px 0 0" }}>
          {JSON.stringify(toolArgs, null, 2)}
        </pre>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={onApprove}
          style={{ padding: "8px 16px", background: "#22c55e", color: "white", border: "none", borderRadius: 4, cursor: "pointer" }}
        >
          Approve
        </button>
        <button
          onClick={onReject}
          style={{ padding: "8px 16px", background: "#ef4444", color: "white", border: "none", borderRadius: 4, cursor: "pointer" }}
        >
          Reject
        </button>
        <button
          onClick={() => {
            const edited = prompt("Edit args (JSON):", JSON.stringify(toolArgs));
            if (edited) onEdit(JSON.parse(edited));
          }}
          style={{ padding: "8px 16px", background: "#3b82f6", color: "white", border: "none", borderRadius: 4, cursor: "pointer" }}
        >
          Edit & Approve
        </button>
      </div>
    </div>
  );
}
```

### Step 4: Frontend — HITL Review Component

**File**: `frontend/src/components/hitl/HITLReview.tsx`

```tsx
"use client";
import { useState } from "react";

interface HITLReviewProps {
  toolName: string;
  originalOutput: string;
  message: string;
  onAccept: (output: string) => void;
}

export function HITLReview({
  toolName,
  originalOutput,
  message,
  onAccept,
}: HITLReviewProps) {
  const [editedOutput, setEditedOutput] = useState(originalOutput);

  return (
    <div style={{
      border: "2px solid #3b82f6",
      borderRadius: 8,
      padding: 16,
      margin: "8px 0",
      backgroundColor: "#eff6ff",
    }}>
      <h4 style={{ margin: "0 0 8px" }}>Review Required</h4>
      <p>{message}</p>
      <p><strong>Tool:</strong> {toolName}</p>
      <textarea
        value={editedOutput}
        onChange={(e) => setEditedOutput(e.target.value)}
        style={{
          width: "100%",
          minHeight: 120,
          padding: 12,
          borderRadius: 4,
          border: "1px solid #ccc",
          fontFamily: "monospace",
          marginBottom: 8,
        }}
      />
      <button
        onClick={() => onAccept(editedOutput)}
        style={{ padding: "8px 16px", background: "#22c55e", color: "white", border: "none", borderRadius: 4, cursor: "pointer" }}
      >
        Accept & Continue
      </button>
    </div>
  );
}
```

### Step 5: Frontend — HITL Form Input Component

**File**: `frontend/src/components/hitl/HITLFormInput.tsx`

```tsx
"use client";
import { useState } from "react";

interface HITLFormInputProps {
  title: string;
  message: string;
  schema: Record<string, unknown>;
  onSubmit: (data: Record<string, unknown>) => void;
}

export function HITLFormInput({
  title,
  message,
  schema,
  onSubmit,
}: HITLFormInputProps) {
  const [formData, setFormData] = useState<Record<string, string>>({});
  const properties = (schema as any)?.properties || {};

  return (
    <div style={{
      border: "2px solid #8b5cf6",
      borderRadius: 8,
      padding: 16,
      margin: "8px 0",
      backgroundColor: "#f5f3ff",
    }}>
      <h4 style={{ margin: "0 0 8px" }}>{title}</h4>
      <p>{message}</p>
      {Object.entries(properties).map(([key, prop]: [string, any]) => (
        <div key={key} style={{ marginBottom: 8 }}>
          <label style={{ display: "block", marginBottom: 4, fontWeight: "bold" }}>
            {key}
          </label>
          {prop.enum ? (
            <select
              value={formData[key] || ""}
              onChange={(e) => setFormData({ ...formData, [key]: e.target.value })}
              style={{ padding: 8, borderRadius: 4, border: "1px solid #ccc", width: "100%" }}
            >
              <option value="">Select...</option>
              {prop.enum.map((v: string) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              value={formData[key] || ""}
              onChange={(e) => setFormData({ ...formData, [key]: e.target.value })}
              style={{ padding: 8, borderRadius: 4, border: "1px solid #ccc", width: "100%" }}
            />
          )}
        </div>
      ))}
      <button
        onClick={() => onSubmit(formData)}
        style={{ padding: "8px 16px", background: "#8b5cf6", color: "white", border: "none", borderRadius: 4, cursor: "pointer" }}
      >
        Submit
      </button>
    </div>
  );
}
```

### Step 6: Frontend — CopilotKit HITL Integration

**File**: `frontend/src/components/copilot/AgentChat.tsx` (extend with HITL)

```tsx
import { useCopilotAction } from "@copilotkit/react-core";
import { HITLApproval } from "../hitl/HITLApproval";
import { HITLReview } from "../hitl/HITLReview";
import { HITLFormInput } from "../hitl/HITLFormInput";

export function AgentChat() {
  // HITL: Approval action
  useCopilotAction({
    name: "hitl_approval",
    description: "Request user approval for a tool call",
    parameters: [
      { name: "tool_name", type: "string" },
      { name: "tool_args", type: "object" },
      { name: "message", type: "string" },
    ],
    render: ({ args, respond }) => (
      <HITLApproval
        toolName={args.tool_name}
        toolArgs={args.tool_args}
        message={args.message}
        onApprove={() => respond?.({ action: "approve" })}
        onReject={() => respond?.({ action: "reject" })}
        onEdit={(editedArgs) => respond?.({ action: "edit", edited_args: editedArgs })}
      />
    ),
  });

  // HITL: Review action
  useCopilotAction({
    name: "hitl_review",
    description: "Request user review of tool output",
    parameters: [
      { name: "tool_name", type: "string" },
      { name: "original_output", type: "string" },
      { name: "message", type: "string" },
    ],
    render: ({ args, respond }) => (
      <HITLReview
        toolName={args.tool_name}
        originalOutput={args.original_output}
        message={args.message}
        onAccept={(output) => respond?.({ edited_output: output })}
      />
    ),
  });

  // HITL: Form input action
  useCopilotAction({
    name: "hitl_form_input",
    description: "Request structured input from user",
    parameters: [
      { name: "title", type: "string" },
      { name: "message", type: "string" },
      { name: "schema", type: "object" },
    ],
    render: ({ args, respond }) => (
      <HITLFormInput
        title={args.title}
        message={args.message}
        schema={args.schema}
        onSubmit={(data) => respond?.(data)}
      />
    ),
  });

  // ... existing render_chart and show_code_result actions from Phase 03

  return (
    <CopilotChat
      instructions="You are a helpful AI assistant."
      labels={{ title: "AI Agent", initial: "How can I help you today?" }}
    />
  );
}
```

### Step 7: HITL Timeout & Auto-Reject

If a user doesn't respond to an approval/review within the configured timeout, the system should auto-reject to prevent graph execution from hanging indefinitely.

**File**: `backend/app/runtime/graphs/react_hitl.py` (enhance interrupt calls)

```python
import asyncio
from app.core.config import settings

HITL_TIMEOUT = settings.HITL_TIMEOUT_SECONDS  # default: 300 (5 minutes)

async def tool_node_with_hitl(state: MessagesState):
    # ... existing code ...

    # For approval pattern, wrap interrupt with timeout
    if tool_name in require_approval:
        try:
            decision = interrupt({
                "type": "approval",
                "tool_name": tool_name,
                "tool_args": tool_args,
                "message": f"Agent wants to call '{tool_name}'. Approve?",
                "timeout_seconds": HITL_TIMEOUT,
            })
        except HITLTimeoutError:
            # Auto-reject on timeout
            results.append(ToolMessage(
                content=f"Tool call '{tool_name}' auto-rejected (approval timeout after {HITL_TIMEOUT}s).",
                tool_call_id=tool_call["id"]
            ))
            continue
```

Frontend shows a countdown timer on HITL components:

```tsx
// Add to HITLApproval.tsx
const [remaining, setRemaining] = useState(timeoutSeconds);
useEffect(() => {
  const interval = setInterval(() => setRemaining(r => r - 1), 1000);
  return () => clearInterval(interval);
}, []);
```

### Step 8: Concurrency Considerations

LangGraph interrupt state is per-graph-instance (tied to `thread_id`). Important notes:

- Each conversation thread has its own interrupt state
- Only one interrupt can be active per thread at a time
- If user navigates away during an interrupt, the state persists in the checkpointer
- Resuming the same thread will re-present the interrupt

---

## Integration Points

- **Phase 02**: Imports `llm_node` and `should_continue` from `react.py` — wraps `tool_node` with HITL logic
- **Phase 03**: HITL components render inline in CopilotKit chat via `useCopilotAction`
- **Phase 04**: HITL wraps the MCP gateway tool calls — same `gateway.call_tool()` interface
- Checkpointer (Phase 02) persists interrupt state

---

## Verification Checklist

- [ ] Create agent with `config.hitl.require_approval: ["web_search"]`
- [ ] Chat → trigger web search → approval dialog appears in chat
- [ ] Click "Approve" → tool executes → result appears
- [ ] Click "Reject" → tool skipped → agent acknowledges rejection
- [ ] Click "Edit & Approve" → modify args → tool executes with edited args
- [ ] Create agent with `config.hitl.require_review: ["send_email"]`
- [ ] Agent generates email → review dialog appears → edit content → accept → modified content used
- [ ] Form input: agent requests structured data → form renders → submit → agent uses data
- [ ] Navigate away during interrupt → return → interrupt state preserved
- [ ] Agent without HITL config → tools execute immediately without interruption

---

## Forward-Looking Notes

- **Phase 07** uses HITL for Plan-Execute (approve/edit plan before execution) and Multi-Agent (approve routing decisions).
- The HITL components here are functional but minimal. A polished UI iteration can improve them later.
- For production, consider rate-limiting interrupts per conversation to prevent agents from spamming approval requests.
- The `hitl_config` in agent config can be extended with per-tool approval thresholds (e.g., only approve if tool cost > $X).
