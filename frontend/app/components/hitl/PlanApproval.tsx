"use client";

import { useState } from "react";

interface PlanApprovalProps {
  plan: string[];
  message: string;
  onResolve: (value: Record<string, unknown>) => void;
}

export default function PlanApproval({ plan, message, onResolve }: PlanApprovalProps) {
  const [steps, setSteps] = useState<string[]>([...plan]);
  const [editing, setEditing] = useState(false);
  const [resolved, setResolved] = useState(false);

  const resolve = (value: Record<string, unknown>) => {
    setResolved(true);
    onResolve(value);
  };

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

  const updateStep = (index: number, value: string) => {
    const newSteps = [...steps];
    newSteps[index] = value;
    setSteps(newSteps);
  };

  const hasEdits = JSON.stringify(steps) !== JSON.stringify(plan);

  if (resolved) {
    return (
      <div style={{ padding: "0.75rem", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "0.5rem", fontSize: "0.875rem", color: "#166534" }}>
        Plan response submitted.
      </div>
    );
  }

  return (
    <div style={{ border: "1px solid #f59e0b", borderRadius: "0.5rem", overflow: "hidden", background: "#fffbeb" }}>
      <div style={{ padding: "0.75rem", borderBottom: "1px solid #fde68a" }}>
        <div style={{ fontWeight: 600, fontSize: "0.875rem", color: "#92400e", marginBottom: "0.25rem" }}>
          Plan Approval
        </div>
        <div style={{ fontSize: "0.8125rem", color: "#78350f" }}>{message}</div>
      </div>

      <div style={{ padding: "0.75rem" }}>
        <div style={{ fontSize: "0.75rem", color: "#92400e", fontWeight: 500, marginBottom: "0.5rem" }}>
          Steps ({steps.length})
        </div>
        <ol style={{ margin: 0, paddingLeft: "1.25rem", listStyleType: "decimal" }}>
          {steps.map((step, i) => (
            <li key={i} style={{ marginBottom: "0.375rem", fontSize: "0.8125rem", color: "#78350f" }}>
              {editing ? (
                <div style={{ display: "flex", gap: "0.25rem", alignItems: "center" }}>
                  <input
                    type="text"
                    value={step}
                    onChange={(e) => updateStep(i, e.target.value)}
                    style={{
                      flex: 1,
                      padding: "0.25rem 0.5rem",
                      fontSize: "0.8125rem",
                      border: "1px solid #d1d5db",
                      borderRadius: "0.25rem",
                    }}
                  />
                  <button
                    onClick={() => moveStep(i, "up")}
                    disabled={i === 0}
                    style={{ padding: "0.125rem 0.375rem", fontSize: "0.75rem", background: "#e5e7eb", border: "none", borderRadius: "0.25rem", cursor: i === 0 ? "default" : "pointer", opacity: i === 0 ? 0.4 : 1 }}
                  >
                    ↑
                  </button>
                  <button
                    onClick={() => moveStep(i, "down")}
                    disabled={i === steps.length - 1}
                    style={{ padding: "0.125rem 0.375rem", fontSize: "0.75rem", background: "#e5e7eb", border: "none", borderRadius: "0.25rem", cursor: i === steps.length - 1 ? "default" : "pointer", opacity: i === steps.length - 1 ? 0.4 : 1 }}
                  >
                    ↓
                  </button>
                  <button
                    onClick={() => removeStep(i)}
                    disabled={steps.length <= 1}
                    style={{ padding: "0.125rem 0.375rem", fontSize: "0.75rem", background: "#fecaca", color: "#991b1b", border: "none", borderRadius: "0.25rem", cursor: steps.length <= 1 ? "default" : "pointer", opacity: steps.length <= 1 ? 0.4 : 1 }}
                  >
                    ×
                  </button>
                </div>
              ) : (
                step
              )}
            </li>
          ))}
        </ol>
      </div>

      <div style={{ padding: "0.75rem", borderTop: "1px solid #fde68a", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        {!editing ? (
          <>
            <button
              onClick={() => resolve({ action: "approve" })}
              style={{ padding: "0.375rem 0.75rem", fontSize: "0.8125rem", fontWeight: 500, color: "#fff", background: "#16a34a", border: "none", borderRadius: "0.375rem", cursor: "pointer" }}
            >
              Approve Plan
            </button>
            <button
              onClick={() => setEditing(true)}
              style={{ padding: "0.375rem 0.75rem", fontSize: "0.8125rem", fontWeight: 500, color: "#fff", background: "#2563eb", border: "none", borderRadius: "0.375rem", cursor: "pointer" }}
            >
              Edit Plan
            </button>
            <button
              onClick={() => resolve({ action: "reject" })}
              style={{ padding: "0.375rem 0.75rem", fontSize: "0.8125rem", fontWeight: 500, color: "#fff", background: "#dc2626", border: "none", borderRadius: "0.375rem", cursor: "pointer" }}
            >
              Reject
            </button>
          </>
        ) : (
          <>
            <button
              onClick={() => resolve(hasEdits ? { action: "edit", edited_plan: steps } : { action: "approve" })}
              style={{ padding: "0.375rem 0.75rem", fontSize: "0.8125rem", fontWeight: 500, color: "#fff", background: hasEdits ? "#2563eb" : "#16a34a", border: "none", borderRadius: "0.375rem", cursor: "pointer" }}
            >
              {hasEdits ? "Approve Edited Plan" : "Approve Plan"}
            </button>
            <button
              onClick={() => { setEditing(false); setSteps([...plan]); }}
              style={{ padding: "0.375rem 0.75rem", fontSize: "0.8125rem", fontWeight: 500, color: "#374151", background: "#e5e7eb", border: "none", borderRadius: "0.375rem", cursor: "pointer" }}
            >
              Cancel Edit
            </button>
            <button
              onClick={() => resolve({ action: "reject" })}
              style={{ padding: "0.375rem 0.75rem", fontSize: "0.8125rem", fontWeight: 500, color: "#fff", background: "#dc2626", border: "none", borderRadius: "0.375rem", cursor: "pointer" }}
            >
              Reject
            </button>
          </>
        )}
      </div>
    </div>
  );
}
