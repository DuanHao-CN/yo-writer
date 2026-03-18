# Phase 05: Code Sandbox — Docker-Based Code Execution

## Meta

| Field | Value |
|-------|-------|
| **Goal** | Secure Docker-based Python code sandbox with MCP tool integration |
| **Prerequisites** | Phase 04 (tool system, MCP gateway) |
| **Effort** | 2-3 days |
| **Key Technologies** | Docker, uv, FastMCP, asyncio subprocess |

---

## Context

This phase adds a code execution sandbox that lets agents run Python code in isolated Docker containers. We use a simplified Docker-based approach for development (ADR-003 specifies gVisor for production, deferred to Phase 10).

The sandbox is exposed as an MCP tool (`code_sandbox`) mounted in the FastMCP gateway, so agents can call it like any other tool. The sandbox manager handles container lifecycle: acquire from pool, execute code, collect results, release/reset.

### Sandbox Architecture

```
Agent (LangGraph)
    └── tool_node → MCP Gateway
                      └── builtin/code-sandbox
                            └── SandboxManager
                                  ├── acquire() → Docker container
                                  ├── execute(code) → stdout/stderr/artifacts
                                  ├── install_packages(uv) → pip packages
                                  └── release() → reset or destroy
```

### Security Constraints (Development)

| Dimension | Limit |
|-----------|-------|
| CPU | 10s wall time |
| Memory | 512MB |
| Disk | 100MB workspace |
| Network | Disabled (`--network none`) |
| Processes | Max 10 child processes |

---

## Data Models

### Alembic Migration

```sql
-- Sandbox Execution Records
CREATE TABLE sandbox_executions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_run_id    UUID REFERENCES agent_runs(id) ON DELETE CASCADE,
    code            TEXT NOT NULL,
    stdout          TEXT,
    stderr          TEXT,
    exit_code       INT,
    artifacts       JSONB DEFAULT '[]',  -- [{name, url, mime_type}]
    cpu_seconds     FLOAT,
    memory_peak_mb  FLOAT,
    duration_ms     INT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## API Endpoints

No new REST endpoints. The sandbox is accessed exclusively via the MCP tool `code_sandbox` through the agent's tool_node.

For debugging/testing:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/sandbox/execute` | Direct sandbox execution (dev only) |

```json
{
  "code": "print('hello world')",
  "packages": ["pandas"],
  "timeout_seconds": 30
}
```

**Response**:

```json
{
  "stdout": "hello world\n",
  "stderr": "",
  "exit_code": 0,
  "artifacts": [],
  "execution_time_ms": 150,
  "memory_peak_mb": 45.2
}
```

---

## Implementation Steps

### Step 1: Sandbox Configuration

**File**: `backend/app/runtime/sandbox/config.py`

```python
from dataclasses import dataclass, field

@dataclass
class SandboxConfig:
    timeout_seconds: int = 30
    max_memory_mb: int = 512
    max_cpu_seconds: int = 10
    network_access: bool = False
    allowed_packages: list[str] = field(default_factory=list)
    workspace_files: dict[str, bytes] = field(default_factory=dict)

@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    artifacts: list[dict]       # [{name, url, mime_type}]
    execution_time_ms: int
    memory_peak_mb: float
```

### Step 2: Sandbox Manager

**File**: `backend/app/runtime/sandbox/manager.py`

```python
import asyncio
import uuid
import time
from app.runtime.sandbox.config import SandboxConfig, ExecutionResult

class SandboxManager:
    """Manages Docker-based Python sandbox containers."""

    def __init__(self, image: str = "python:3.12-slim"):
        self.image = image

    async def execute(self, code: str, config: SandboxConfig | None = None) -> ExecutionResult:
        """Run Python code in an isolated Docker container."""
        config = config or SandboxConfig()
        container_name = f"sandbox-{uuid.uuid4().hex[:12]}"
        start = time.monotonic()

        # Build docker run command with resource limits
        cmd = [
            "docker", "run", "--rm",
            "--name", container_name,
            "--memory", f"{config.max_memory_mb}m",
            "--cpus", "1",
            "--network", "none" if not config.network_access else "bridge",
            "--pids-limit", "10",
            "--read-only",
            "--tmpfs", "/tmp:size=100m",
            "--tmpfs", "/workspace:size=100m",
            "-w", "/workspace",
            self.image,
            "python", "-c", code,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=config.timeout_seconds,
            )
            elapsed = int((time.monotonic() - start) * 1000)

            return ExecutionResult(
                stdout=stdout.decode(errors="replace"),
                stderr=stderr.decode(errors="replace"),
                exit_code=proc.returncode or 0,
                artifacts=[],
                execution_time_ms=elapsed,
                memory_peak_mb=0.0,  # Docker stats would provide this
            )
        except asyncio.TimeoutError:
            # Kill the container on timeout
            await asyncio.create_subprocess_exec("docker", "kill", container_name)
            elapsed = int((time.monotonic() - start) * 1000)
            return ExecutionResult(
                stdout="",
                stderr=f"Execution timed out after {config.timeout_seconds}s",
                exit_code=-1,
                artifacts=[],
                execution_time_ms=elapsed,
                memory_peak_mb=0.0,
            )

    async def execute_with_packages(
        self, code: str, packages: list[str], config: SandboxConfig | None = None
    ) -> ExecutionResult:
        """Run code with pre-installed packages using uv."""
        config = config or SandboxConfig()

        # Build a script that installs packages then runs user code
        install_script = ""
        if packages:
            pkg_list = " ".join(packages)
            install_script = f"import subprocess; subprocess.run(['uv', 'pip', 'install', '--quiet', {', '.join(repr(p) for p in packages)}], check=True)\n"

        full_code = install_script + code
        return await self.execute(full_code, config)

# Singleton
sandbox_manager = SandboxManager()
```

### Step 3: MCP Tool — code_sandbox

**File**: `backend/app/runtime/mcp_gateway.py` (add to existing file)

```python
from app.runtime.sandbox.manager import sandbox_manager

# Built-in: code sandbox
builtin_sandbox = FastMCP("builtin-code-sandbox")

@builtin_sandbox.tool
async def code_sandbox(
    code: str,
    packages: list[str] | None = None,
    timeout_seconds: int = 30,
) -> str:
    """Execute Python code in a secure sandbox environment.

    Args:
        code: Python code to execute
        packages: Optional list of pip packages to install before execution
        timeout_seconds: Maximum execution time in seconds
    """
    from app.runtime.sandbox.config import SandboxConfig

    config = SandboxConfig(timeout_seconds=timeout_seconds)
    if packages:
        result = await sandbox_manager.execute_with_packages(code, packages, config)
    else:
        result = await sandbox_manager.execute(code, config)

    output_parts = []
    if result.stdout:
        output_parts.append(f"Output:\n{result.stdout}")
    if result.stderr:
        output_parts.append(f"Errors:\n{result.stderr}")
    output_parts.append(f"Exit code: {result.exit_code}")
    output_parts.append(f"Execution time: {result.execution_time_ms}ms")

    return "\n".join(output_parts)

# Mount in gateway
gateway.mount(builtin_sandbox, namespace="builtin/code-sandbox")
```

### Step 4: Record Sandbox Executions

**File**: `backend/app/models/sandbox.py`

```python
class SandboxExecution(Base):
    __tablename__ = "sandbox_executions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_run_id = Column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"))
    code = Column(Text, nullable=False)
    stdout = Column(Text)
    stderr = Column(Text)
    exit_code = Column(Integer)
    artifacts = Column(JSONB, default=[])
    cpu_seconds = Column(Float)
    memory_peak_mb = Column(Float)
    duration_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

Add recording to the `code_sandbox` tool — after execution, write a row to `sandbox_executions`.

### Step 5: Seed code_sandbox as built-in tool

Add to `BUILTIN_TOOLS` in `tool_service.py`:

```python
{"name": "Code Sandbox", "slug": "code-sandbox", "type": "builtin",
 "mcp_uri": "mcp://builtin/code-sandbox",
 "description": "Execute Python code in a secure sandbox"},
```

### Step 6: Dev-only direct execution endpoint

**File**: `backend/app/api/v1/sandbox.py`

```python
router = APIRouter(prefix="/api/v1/sandbox", tags=["sandbox"])

@router.post("/execute")
async def execute_code(data: SandboxExecuteRequest):
    result = await sandbox_manager.execute(data.code, SandboxConfig(
        timeout_seconds=data.timeout_seconds,
    ))
    return result
```

---

## Integration Points

- **Phase 04**: `code_sandbox` MCP tool is mounted in the same gateway as web_search and file_ops
- **Phase 04**: Tool calls are recorded in `tool_calls` table; sandbox also records in `sandbox_executions`
- **Phase 03**: Code execution results stream back through AG-UI to CopilotKit chat
- **Phase 02**: Sandbox executions reference `agent_runs` for traceability

---

## Verification Checklist

- [ ] `uv run alembic upgrade head` — creates `sandbox_executions` table
- [ ] `POST /api/v1/sandbox/execute` with `{"code": "print(2+2)"}` → returns `{"stdout": "4\n", ...}`
- [ ] Docker container starts and is cleaned up after execution
- [ ] Timeout works: code with `time.sleep(60)` is killed after configured timeout
- [ ] Memory limit works: code allocating >512MB is OOM killed
- [ ] Network disabled: code attempting `urllib.request.urlopen(...)` fails
- [ ] Chat with agent → "write Python code for fibonacci(10)" → agent calls `code_sandbox` → result appears in chat
- [ ] `sandbox_executions` table has a record with code, stdout, timing
- [ ] `tool_calls` table also has a record for the code_sandbox call

---

## Forward-Looking Notes

- **Phase 06** (HITL) can require approval before code execution — useful for security-sensitive agents.
- **Phase 10** replaces Docker containers with gVisor (`runsc` runtime) for production-grade isolation. The `SandboxManager` interface stays the same.
- Package installation via `uv` in the sandbox should use a shared cache volume for speed. For dev, the simple approach works. Production should pre-build images with common packages.
- Artifact collection (generated plots, CSVs) requires mounting a volume and uploading to MinIO — defer to a later iteration.
