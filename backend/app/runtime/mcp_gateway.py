"""FastMCP gateway — mounts builtin tool servers and exposes a unified interface.

Phase 04: builtin mock tools (web-search, file-ops).
Phase 05: code-sandbox (Docker-based Python execution).
Future phases add user-registered MCP tool servers.
"""

import logging
from typing import Any

from fastmcp import Client, FastMCP

from app.runtime.sandbox.config import SandboxConfig
from app.runtime.sandbox.manager import sandbox_manager

logger = logging.getLogger(__name__)

# ---- Builtin tool servers ----

builtin_search = FastMCP("builtin-web-search")
builtin_files = FastMCP("builtin-file-ops")
builtin_sandbox = FastMCP("builtin-code-sandbox")


@builtin_search.tool
def web_search(query: str) -> str:
    """Search the web for information."""
    return f"[Mock] Search results for: {query}"


@builtin_files.tool
def read_file(path: str) -> str:
    """Read the contents of a file."""
    return f"[Mock] Contents of file: {path}"


@builtin_files.tool
def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    return f"[Mock] Wrote {len(content)} chars to {path}"


@builtin_sandbox.tool
async def code_sandbox(
    code: str,
    packages: list[str] | None = None,
    timeout_seconds: int = 30,
) -> str:
    """Execute Python code in a secure Docker sandbox."""
    config = SandboxConfig(timeout_seconds=timeout_seconds)

    if packages:
        result = await sandbox_manager.execute_with_packages(code, packages, config)
    else:
        result = await sandbox_manager.execute(code, config)

    parts = [
        f"Exit code: {result.exit_code}",
        f"Duration: {result.execution_time_ms}ms",
    ]
    if result.stdout:
        parts.append(f"--- stdout ---\n{result.stdout}")
    if result.stderr:
        parts.append(f"--- stderr ---\n{result.stderr}")
    return "\n".join(parts)


# ---- Gateway (mounts all builtin servers) ----

gateway = FastMCP("YoAgent-MCP-Gateway")
gateway.mount(builtin_search, namespace="builtin_web-search")
gateway.mount(builtin_files, namespace="builtin_file-ops")
gateway.mount(builtin_sandbox, namespace="builtin_code-sandbox")


async def get_mcp_tool_schemas() -> list[dict[str, Any]]:
    """Return all gateway tools in OpenAI function-calling format for LLM binding."""
    client = Client(gateway)
    async with client:
        tools = await client.list_tools()

    result: list[dict[str, Any]] = []
    for tool in tools:
        schema: dict[str, Any] = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema or {"type": "object", "properties": {}},
            },
        }
        result.append(schema)
    return result


async def call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    """Call a tool on the gateway by name. Returns the result as a string."""
    client = Client(gateway)
    async with client:
        result = await client.call_tool(tool_name, arguments)

    if result.is_error:
        error_text = str(result.content) if result.content else "Unknown error"
        raise RuntimeError(f"Tool '{tool_name}' failed: {error_text}")

    # Extract text from result
    if result.content:
        parts = []
        for block in result.content:
            if hasattr(block, "text"):
                parts.append(block.text)
            else:
                parts.append(str(block))
        return "\n".join(parts)

    return str(result.data) if result.data is not None else ""
