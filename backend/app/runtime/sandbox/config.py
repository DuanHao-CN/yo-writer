"""Sandbox configuration and result dataclasses."""

from dataclasses import dataclass, field


@dataclass
class SandboxConfig:
    timeout_seconds: int = 30
    max_memory_mb: int = 512
    max_cpu_seconds: int = 10
    network_access: bool = False
    allowed_packages: list[str] = field(default_factory=list)
    workspace_files: dict[str, str] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    artifacts: list[dict] = field(default_factory=list)
    execution_time_ms: int = 0
    memory_peak_mb: float = 0.0
