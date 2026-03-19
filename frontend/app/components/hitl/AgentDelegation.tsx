"use client";

import { useState } from "react";

interface AgentDelegationProps {
  nextAgent: string;
  availableAgents: string[];
  message: string;
  onResolve: (value: Record<string, unknown>) => void;
}

export default function AgentDelegation({ nextAgent, availableAgents, message, onResolve }: AgentDelegationProps) {
  const [resolved, setResolved] = useState(false);

  const resolve = (value: Record<string, unknown>) => {
    setResolved(true);
    onResolve(value);
  };

  const otherAgents = availableAgents.filter((a) => a !== nextAgent);

  if (resolved) {
    return (
      <div style={{ padding: "0.75rem", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "0.5rem", fontSize: "0.875rem", color: "#166534" }}>
        Delegation response submitted.
      </div>
    );
  }

  return (
    <div style={{ border: "1px solid #8b5cf6", borderRadius: "0.5rem", overflow: "hidden", background: "#f5f3ff" }}>
      <div style={{ padding: "0.75rem", borderBottom: "1px solid #c4b5fd" }}>
        <div style={{ fontWeight: 600, fontSize: "0.875rem", color: "#5b21b6", marginBottom: "0.25rem" }}>
          Agent Delegation
        </div>
        <div style={{ fontSize: "0.8125rem", color: "#6d28d9" }}>{message}</div>
      </div>

      <div style={{ padding: "0.75rem" }}>
        <div style={{ fontSize: "0.8125rem", color: "#5b21b6" }}>
          Supervisor wants to delegate to: <strong style={{ textTransform: "capitalize" }}>{nextAgent}</strong>
        </div>
      </div>

      <div style={{ padding: "0.75rem", borderTop: "1px solid #c4b5fd", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        <button
          onClick={() => resolve({ action: "approve" })}
          style={{ padding: "0.375rem 0.75rem", fontSize: "0.8125rem", fontWeight: 500, color: "#fff", background: "#16a34a", border: "none", borderRadius: "0.375rem", cursor: "pointer" }}
        >
          Approve → {nextAgent}
        </button>
        {otherAgents.map((agent) => (
          <button
            key={agent}
            onClick={() => resolve({ action: "redirect", redirect_to: agent })}
            style={{ padding: "0.375rem 0.75rem", fontSize: "0.8125rem", fontWeight: 500, color: "#fff", background: "#2563eb", border: "none", borderRadius: "0.375rem", cursor: "pointer", textTransform: "capitalize" }}
          >
            Redirect → {agent}
          </button>
        ))}
        <button
          onClick={() => resolve({ action: "stop" })}
          style={{ padding: "0.375rem 0.75rem", fontSize: "0.8125rem", fontWeight: 500, color: "#fff", background: "#dc2626", border: "none", borderRadius: "0.375rem", cursor: "pointer" }}
        >
          Stop
        </button>
      </div>
    </div>
  );
}
