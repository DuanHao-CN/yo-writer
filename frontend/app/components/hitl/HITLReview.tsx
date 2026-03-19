"use client";

import { useState } from "react";

interface HITLReviewProps {
  toolName: string;
  originalOutput: string;
  message: string;
  onResolve: (value: Record<string, unknown>) => void;
}

export default function HITLReview({ toolName, originalOutput, message, onResolve }: HITLReviewProps) {
  const [editedOutput, setEditedOutput] = useState(originalOutput);
  const [resolved, setResolved] = useState(false);

  const resolve = (value: Record<string, unknown>) => {
    setResolved(true);
    onResolve(value);
  };

  if (resolved) {
    return (
      <div style={{ padding: "0.75rem", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "0.5rem", fontSize: "0.875rem", color: "#166534" }}>
        Review submitted.
      </div>
    );
  }

  return (
    <div style={{ border: "1px solid #93c5fd", borderRadius: "0.5rem", overflow: "hidden", background: "#eff6ff" }}>
      <div style={{ padding: "0.75rem", borderBottom: "1px solid #bfdbfe" }}>
        <div style={{ fontWeight: 600, fontSize: "0.875rem", color: "#1e40af", marginBottom: "0.25rem" }}>
          Review Output
        </div>
        <div style={{ fontSize: "0.8125rem", color: "#1e3a8a" }}>{message}</div>
      </div>

      <div style={{ padding: "0.75rem" }}>
        <div style={{ fontSize: "0.75rem", color: "#1e40af", fontWeight: 500, marginBottom: "0.25rem" }}>
          Tool: {toolName}
        </div>
        <textarea
          value={editedOutput}
          onChange={(e) => setEditedOutput(e.target.value)}
          style={{
            width: "100%",
            minHeight: "100px",
            fontFamily: "monospace",
            fontSize: "0.8125rem",
            padding: "0.5rem",
            border: "1px solid #d1d5db",
            borderRadius: "0.375rem",
            resize: "vertical",
            boxSizing: "border-box",
          }}
        />
      </div>

      <div style={{ padding: "0.75rem", borderTop: "1px solid #bfdbfe", display: "flex", gap: "0.5rem" }}>
        <button
          onClick={() => resolve({ edited_output: editedOutput })}
          style={{ padding: "0.375rem 0.75rem", fontSize: "0.8125rem", fontWeight: 500, color: "#fff", background: "#16a34a", border: "none", borderRadius: "0.375rem", cursor: "pointer" }}
        >
          Accept & Continue
        </button>
      </div>
    </div>
  );
}
