"""Docker-based Python code sandbox manager.

Runs user code in isolated Docker containers with resource limits.
Dev-mode isolation (Docker); Phase 10 upgrades to gVisor.
"""

import asyncio
import logging
import time

from app.runtime.sandbox.config import ExecutionResult, SandboxConfig

logger = logging.getLogger(__name__)

_DOCKER_IMAGE = "python:3.12-slim"


class SandboxManager:
    def __init__(self, image: str = _DOCKER_IMAGE) -> None:
        self.image = image

    async def execute(
        self, code: str, config: SandboxConfig | None = None
    ) -> ExecutionResult:
        """Execute Python code in an isolated Docker container."""
        cfg = config or SandboxConfig()

        docker_cmd = self._build_docker_cmd(cfg)
        # Pass code via stdin to avoid shell-escaping issues
        docker_cmd += [self.image, "python", "-c", code]

        return await self._run(docker_cmd, cfg.timeout_seconds)

    async def execute_with_packages(
        self,
        code: str,
        packages: list[str],
        config: SandboxConfig | None = None,
    ) -> ExecutionResult:
        """Execute Python code after installing pip packages.

        Network is enabled for package install. A note is added to stderr.
        """
        cfg = config or SandboxConfig()

        # Build a shell script: install packages then run code
        safe_packages = " ".join(packages)
        script = (
            f"pip install --quiet {safe_packages} 2>&1 && "
            f"python -c {_shell_quote(code)}"
        )

        docker_cmd = self._build_docker_cmd(cfg, network_enabled=True)
        docker_cmd += [self.image, "sh", "-c", script]

        result = await self._run(docker_cmd, cfg.timeout_seconds)
        result.stderr = (
            f"[note] Network enabled for package install: {safe_packages}\n"
            + result.stderr
        )
        return result

    def _build_docker_cmd(
        self, cfg: SandboxConfig, network_enabled: bool = False
    ) -> list[str]:
        cmd = [
            "docker", "run", "--rm",
            f"--memory={cfg.max_memory_mb}m",
            f"--memory-swap={cfg.max_memory_mb}m",
            "--cpus=1",
            "--pids-limit=10",
            "--read-only",
            "--tmpfs", "/tmp:size=100m",
            "--tmpfs", "/workspace:size=100m",
        ]
        if not (cfg.network_access or network_enabled):
            cmd.append("--network=none")
        return cmd

    async def _run(self, cmd: list[str], timeout: int) -> ExecutionResult:
        start = time.monotonic()

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except TimeoutError:
            logger.warning("Sandbox execution timed out after %ds, killing", timeout)
            try:
                proc.kill()
                await proc.wait()
            except ProcessLookupError:
                pass
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return ExecutionResult(
                stdout="",
                stderr=f"Execution timed out after {timeout}s",
                exit_code=137,
                execution_time_ms=elapsed_ms,
            )

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return ExecutionResult(
            stdout=stdout_bytes.decode(errors="replace"),
            stderr=stderr_bytes.decode(errors="replace"),
            exit_code=proc.returncode or 0,
            execution_time_ms=elapsed_ms,
        )


def _shell_quote(s: str) -> str:
    """Single-quote a string for sh -c."""
    return "'" + s.replace("'", "'\\''") + "'"


sandbox_manager = SandboxManager()
