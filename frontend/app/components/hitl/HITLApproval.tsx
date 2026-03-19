"use client";

import { useState } from "react";

interface HITLApprovalProps {
  toolName: string;
  toolArgs: Record<string, unknown>;
  message: string;
  onResolve: (value: Record<string, unknown>) => void;
}

export default function HITLApproval({ toolName, toolArgs, message, onResolve }: HITLApprovalProps) {
  const [editing, setEditing] = useState(false);
  const [editedArgs, setEditedArgs] = useState(JSON.stringify(toolArgs, null, 2));
  const [resolved, setResolved] = useState(false);

  const resolve = (value: Record<string, unknown>) => {
    setResolved(true);
    onResolve(value);
  };

  if (resolved) {
    return (
      <div style={{ padding: "0.75rem", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "0.5rem", fontSize: "0.875rem", color: "#166534" }}>
        Response submitted.
      </div>
    );
  }

  return (
    <div style={{ border: "1px solid #fbbf24", borderRadius: "0.5rem", overflow: "hidden", background: "#fffbeb" }}>
      <div style={{ padding: "0.75rem", borderBottom: "1px solid #fde68a" }}>
        <div style={{ fontWeight: 600, fontSize: "0.875rem", color: "#92400e", marginBottom: "0.25rem" }}>
          Approval Required
        </div>
        <div style={{ fontSize: "0.8125rem", color: "#78350f" }}>{message}</div>
      </div>

      <div style={{ padding: "0.75rem" }}>
        <div style={{ fontSize: "0.75rem", color: "#92400e", fontWeight: 500, marginBottom: "0.25rem" }}>
          Tool: {toolName}
        </div>
        {editing ? (
          <textarea
            value={editedArgs}
            onChange={(e) => setEditedArgs(e.target.value)}
            style={{
              width: "100%",
              minHeight: "80px",
              fontFamily: "monospace",
              fontSize: "0.8125rem",
              padding: "0.5rem",
              border: "1px solid #d1d5db",
              borderRadius: "0.375rem",
              resize: "vertical",
              boxSizing: "border-box",
            }}
          />
        ) : (
          <pre style={{ margin: 0, fontSize: "0.8125rem", background: "#fef3c7", padding: "0.5rem", borderRadius: "0.375rem", whiteSpace: "pre-wrap", overflowX: "auto" }}>
            {JSON.stringify(toolArgs, null, 2)}
          </pre>
        )}
      </div>

      <div style={{ padding: "0.75rem", borderTop: "1px solid #fde68a", display: "flex", gap: "0.5rem" }}>
        <button
          onClick={() => resolve({ action: "approve" })}
          style={{ padding: "0.375rem 0.75rem", fontSize: "0.8125rem", fontWeight: 500, color: "#fff", background: "#16a34a", border: "none", borderRadius: "0.375rem", cursor: "pointer" }}
        >
          Approve
        </button>
        <button
          onClick={() => resolve({ action: "reject" })}
          style={{ padding: "0.375rem 0.75rem", fontSize: "0.8125rem", fontWeight: 500, color: "#fff", background: "#dc2626", border: "none", borderRadius: "0.375rem", cursor: "pointer" }}
        >
          Reject
        </button>
        {editing ? (
          <button
            onClick={() => {
              try {
                const parsed = JSON.parse(editedArgs);
                resolve({ action: "edit", edited_args: parsed });
              } catch {
                alert("Invalid JSON");
              }
            }}
            style={{ padding: "0.375rem 0.75rem", fontSize: "0.8125rem", fontWeight: 500, color: "#fff", background: "#2563eb", border: "none", borderRadius: "0.375rem", cursor: "pointer" }}
          >
            Save & Approve
          </button>
        ) : (
          <button
            onClick={() => setEditing(true)}
            style={{ padding: "0.375rem 0.75rem", fontSize: "0.8125rem", fontWeight: 500, color: "#fff", background: "#2563eb", border: "none", borderRadius: "0.375rem", cursor: "pointer" }}
          >
            Edit & Approve
          </button>
        )}
      </div>
    </div>
  );
}
