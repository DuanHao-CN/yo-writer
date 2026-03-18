from pydantic import BaseModel, Field


class SandboxExecuteRequest(BaseModel):
    code: str
    packages: list[str] | None = None
    timeout_seconds: int = Field(default=30, ge=1, le=120)


class SandboxExecuteResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    artifacts: list[dict] = Field(default_factory=list)
    execution_time_ms: int
    memory_peak_mb: float
