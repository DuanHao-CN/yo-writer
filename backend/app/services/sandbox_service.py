"""Sandbox service — code execution and recording."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sandbox import SandboxExecution
from app.runtime.sandbox.config import ExecutionResult, SandboxConfig
from app.runtime.sandbox.manager import sandbox_manager


async def execute_code(
    code: str,
    packages: list[str] | None = None,
    timeout_seconds: int = 30,
) -> ExecutionResult:
    """Execute Python code in the sandbox, optionally installing packages first."""
    config = SandboxConfig(timeout_seconds=timeout_seconds)

    if packages:
        return await sandbox_manager.execute_with_packages(code, packages, config)
    return await sandbox_manager.execute(code, config)


async def record_execution(
    db: AsyncSession,
    agent_run_id: uuid.UUID,
    code: str,
    result: ExecutionResult,
) -> SandboxExecution:
    """Persist a sandbox execution result to the database."""
    execution = SandboxExecution(
        agent_run_id=agent_run_id,
        code=code,
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
        artifacts=result.artifacts,
        memory_peak_mb=result.memory_peak_mb,
        duration_ms=result.execution_time_ms,
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)
    return execution
