"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface Agent {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  icon: string | null;
  status: string;
}

interface AgentListResponse {
  items: Agent[];
  total: number;
  page: number;
  page_size: number;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/v1/agents`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: AgentListResponse) => {
        setAgents(data.items);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div style={{ padding: "2rem", textAlign: "center" }}>
        <p>Loading agents...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "2rem", textAlign: "center", color: "#ef4444" }}>
        <p>Failed to load agents: {error}</p>
        <p style={{ fontSize: "0.875rem", color: "#6b7280", marginTop: "0.5rem" }}>
          Make sure the backend is running at {API_URL}
        </p>
      </div>
    );
  }

  if (agents.length === 0) {
    return (
      <div style={{ padding: "2rem", textAlign: "center" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: "bold", marginBottom: "1rem" }}>Agents</h1>
        <p style={{ color: "#6b7280" }}>No agents yet.</p>
        <p style={{ fontSize: "0.875rem", color: "#9ca3af", marginTop: "0.5rem" }}>
          Create one via <code>POST /api/v1/agents</code>
        </p>
      </div>
    );
  }

  return (
    <div style={{ padding: "2rem", maxWidth: "800px", margin: "0 auto" }}>
      <h1 style={{ fontSize: "1.5rem", fontWeight: "bold", marginBottom: "1.5rem" }}>Agents</h1>
      <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))" }}>
        {agents.map((agent) => (
          <Link
            key={agent.id}
            href={`/chat/${agent.slug}`}
            style={{
              display: "block",
              padding: "1.25rem",
              border: "1px solid #e5e7eb",
              borderRadius: "0.5rem",
              textDecoration: "none",
              color: "inherit",
              transition: "border-color 0.15s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#3b82f6")}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#e5e7eb")}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.5rem" }}>
              <span style={{ fontSize: "1.5rem" }}>{agent.icon || "🤖"}</span>
              <h2 style={{ fontSize: "1.125rem", fontWeight: 600 }}>{agent.name}</h2>
            </div>
            {agent.description && (
              <p style={{ fontSize: "0.875rem", color: "#6b7280", margin: 0 }}>
                {agent.description}
              </p>
            )}
          </Link>
        ))}
      </div>
    </div>
  );
}
