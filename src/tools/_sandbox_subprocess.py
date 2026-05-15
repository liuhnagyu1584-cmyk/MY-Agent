import asyncio
import os
import time
from typing import Optional

from ._sandbox_manager import ExecutionResult
from ._sandbox_utils import extract_imports, truncate_output


class SubprocessSandbox:
    def __init__(
        self,
        workspace_root: str,
        max_timeout: int = 300,
        max_memory: int = 512,
        max_cpu: float = 1.0,
        max_output_size: int = 1_048_576,
    ):
        self.workspace_root = workspace_root
        self.max_timeout = max_timeout
        self.max_output_size = max_output_size
        self.error: Optional[str] = None
        self._process = None

    async def execute_code(
        self,
        code: str,
        language: str = "python",
        timeout: int = 30,
        requirements: Optional[list[str]] = None,
    ) -> ExecutionResult:
        start_time = time.time()
        timeout = min(timeout, self.max_timeout)

        if requirements:
            ok = await self._install_dependencies(requirements, timeout)
            if not ok:
                return ExecutionResult(
                    return_code=-1,
                    error="DependencyInstallError: 依赖安装失败",
                    execution_time=round(time.time() - start_time, 2),
                )

        cmd = self._build_command(code, language)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace_root,
            )
            self._process = process

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            if self._process:
                try:
                    self._process.kill()
                except Exception:
                    pass
            return ExecutionResult(
                return_code=-1,
                stderr="执行超时",
                timeout=True,
                execution_time=round(time.time() - start_time, 2),
            )
        except Exception as e:
            return ExecutionResult(
                return_code=-1,
                error=f"ExecutionError: {e}",
                execution_time=round(time.time() - start_time, 2),
            )

        stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
        stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

        stdout = truncate_output(stdout, self.max_output_size)
        stderr = truncate_output(stderr, self.max_output_size)

        return ExecutionResult(
            return_code=process.returncode or 0,
            stdout=stdout,
            stderr=stderr,
            timeout=False,
            execution_time=round(time.time() - start_time, 2),
        )

    def _build_command(self, code: str, language: str) -> list[str]:
        if language == "python":
            return ["python", "-c", code]
        elif language == "javascript":
            return ["node", "-e", code]
        else:
            return ["bash", "-c", code]

    async def _install_dependencies(
        self, requirements: list[str], timeout: int
    ) -> bool:
        if not requirements:
            return True
        req_str = " ".join(requirements)
        try:
            process = await asyncio.create_subprocess_exec(
                "pip", "install", *requirements,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace_root,
            )
            await asyncio.wait_for(process.communicate(), timeout=timeout + 10)
            return process.returncode == 0
        except asyncio.TimeoutError:
            return False
        except Exception:
            return False

    async def cleanup(self):
        self._process = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.cleanup()
