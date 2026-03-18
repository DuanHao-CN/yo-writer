"use client";

import { use } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ChatLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ agent_slug: string }>;
}) {
  const { agent_slug } = use(params);

  return (
    <CopilotKit runtimeUrl={`${API_URL}/copilotkit`} agent={agent_slug}>
      {children}
    </CopilotKit>
  );
}
