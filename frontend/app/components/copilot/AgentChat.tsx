"use client";

import { CopilotChat } from "@copilotkit/react-ui";
import { useCopilotAction } from "@copilotkit/react-core";

export default function AgentChat() {
  // Generative UI: render_chart placeholder
  useCopilotAction({
    name: "render_chart",
    description: "Render a chart visualization",
    parameters: [
      { name: "title", type: "string", description: "Chart title" },
      { name: "data", type: "string", description: "Chart data as JSON string" },
    ],
    handler: async () => {},
    render: ({ args }) => (
      <div
        style={{
          padding: "1rem",
          border: "1px solid #e5e7eb",
          borderRadius: "0.5rem",
          background: "#f9fafb",
        }}
      >
        <strong>{args?.title || "Chart"}</strong>
        <p style={{ fontSize: "0.875rem", color: "#6b7280" }}>
          Chart visualization placeholder — data: {args?.data || "..."}
        </p>
      </div>
    ),
  });

  // Generative UI: show_code_result
  useCopilotAction({
    name: "show_code_result",
    description: "Display code and its execution output",
    parameters: [
      { name: "code", type: "string", description: "The code that was executed" },
      { name: "output", type: "string", description: "The execution output" },
    ],
    handler: async () => {},
    render: ({ args }) => (
      <div
        style={{
          borderRadius: "0.5rem",
          overflow: "hidden",
          border: "1px solid #e5e7eb",
        }}
      >
        <div style={{ background: "#1f2937", color: "#e5e7eb", padding: "0.75rem", fontSize: "0.8125rem" }}>
          <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{args?.code || ""}</pre>
        </div>
        {args?.output && (
          <div style={{ background: "#f3f4f6", padding: "0.75rem", fontSize: "0.8125rem" }}>
            <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{args.output}</pre>
          </div>
        )}
      </div>
    ),
  });

  return (
    <CopilotChat
      className="copilot-chat"
      labels={{
        title: "Agent Chat",
        initial: "Hello! How can I help you today?",
        placeholder: "Type a message...",
      }}
    />
  );
}
