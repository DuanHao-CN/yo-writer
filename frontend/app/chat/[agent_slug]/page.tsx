"use client";

import { use } from "react";
import Link from "next/link";
import AgentChat from "../../components/copilot/AgentChat";

export default function ChatPage({
  params,
}: {
  params: Promise<{ agent_slug: string }>;
}) {
  const { agent_slug } = use(params);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: "1rem",
          padding: "0.75rem 1.5rem",
          borderBottom: "1px solid #e5e7eb",
        }}
      >
        <Link href="/agents" style={{ color: "#6b7280", textDecoration: "none", fontSize: "0.875rem" }}>
          ← Agents
        </Link>
        <h1 style={{ fontSize: "1rem", fontWeight: 600, margin: 0 }}>{agent_slug}</h1>
      </header>
      <div style={{ flex: 1, overflow: "hidden" }}>
        <AgentChat />
      </div>
    </div>
  );
}
