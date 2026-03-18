"""Dev-only direct code execution endpoint."""

from fastapi import APIRouter

from app.schemas.sandbox import SandboxExecuteRequest, SandboxExecuteResponse
from app.services import sandbox_service

router = APIRouter(prefix="/api/v1/sandbox", tags=["sandbox"])


@router.post("/execute", response_model=SandboxExecuteResponse)
async def execute_code(data: SandboxExecuteRequest) -> SandboxExecuteResponse:
    result = await sandbox_service.execute_code(
        code=data.code,
        packages=data.packages,
        timeout_seconds=data.timeout_seconds,
    )
    return SandboxExecuteResponse(
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
        artifacts=result.artifacts,
        execution_time_ms=result.execution_time_ms,
        memory_peak_mb=result.memory_peak_mb,
    )
