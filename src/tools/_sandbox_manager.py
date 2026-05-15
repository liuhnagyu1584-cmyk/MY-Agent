import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

from ._docker_config import (
    SANDBOX_IMAGES,
    get_init_script,
    get_pip_install_command,
    get_resource_config,
    wrap_python_command,
)
from ._sandbox_utils import extract_imports, truncate_output


@dataclass
class ExecutionResult:
    return_code: int = -1
    stdout: str = ""
    stderr: str = ""
    timeout: bool = False
    execution_time: float = 0.0
    error: Optional[str] = None


class SandboxManager:
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
        self.max_memory = max_memory
        self.max_cpu = max_cpu
        self.max_output_size = max_output_size
        self.container = None
        self.error: Optional[str] = None

        try:
            import docker
            self.docker_client = docker.from_env()
            self.docker_client.ping()
        except Exception as e:
            self.docker_client = None
            self.error = f"Docker 连接失败: {e}"

    async def initialize_container(self, language: str) -> bool:
        if self.docker_client is None:
            self.error = "Docker 未连接"
            return False

        image = SANDBOX_IMAGES.get(language)
        if image is None:
            self.error = f"不支持的语言: {language}"
            return False

        try:
            try:
                self.docker_client.images.get(image)
            except Exception:
                print(f"[沙箱] 正在拉取镜像 {image}...")
                self.docker_client.images.pull(image)

            resource_config = get_resource_config(self.max_memory, self.max_cpu)

            self.container = self.docker_client.containers.create(
                image,
                command="sleep 3600",
                working_dir="/workspace",
                volumes={self.workspace_root: {"bind": "/workspace", "mode": "rw"}},
                network_mode="none",
                detach=True,
                tty=False,
                stdin_open=False,
                **resource_config,
            )
            self.container.start()

            init_script = get_init_script(language)
            if init_script:
                exit_code, _, stderr = await self._exec_in_container(init_script)
                if exit_code != 0:
                    self.error = f"容器初始化失败: {stderr}"
                    return False

            return True
        except Exception as e:
            self.error = f"容器创建失败: {e}"
            return False

    async def _exec_in_container(
        self, command: str, timeout: int = 30
    ) -> tuple[int, str, str]:
        if self.container is None:
            return (-1, "", "容器未初始化")
        try:
            result = self.container.exec_run(
                ["sh", "-c", command],
                stdout=True,
                stderr=True,
                demux=True,
            )
            out = result.output
            if out is None:
                return (result.exit_code, "", "")
            stdout_bytes, stderr_bytes = out
            stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
            return (result.exit_code, stdout, stderr)
        except Exception as e:
            return (-1, "", str(e))

    async def execute_code(
        self,
        code: str,
        language: str = "python",
        timeout: int = 30,
        requirements: Optional[list[str]] = None,
    ) -> ExecutionResult:
        start_time = time.time()
        timeout = min(timeout, self.max_timeout)

        if self.container is None:
            ok = await self.initialize_container(language)
            if not ok:
                return ExecutionResult(
                    return_code=-1,
                    error=f"ContainerInitError: {self.error}",
                    execution_time=round(time.time() - start_time, 2),
                )

        if requirements:
            ok = await self._install_dependencies(requirements, timeout)
            if not ok:
                return ExecutionResult(
                    return_code=-1,
                    error="DependencyInstallError: 依赖安装失败",
                    execution_time=round(time.time() - start_time, 2),
                )
        elif language == "python":
            pkgs = extract_imports(code)
            if pkgs:
                ok = await self._install_dependencies(pkgs, timeout)
                if not ok:
                    return ExecutionResult(
                        return_code=-1,
                        error="DependencyInstallError: 自动检测依赖安装失败",
                        execution_time=round(time.time() - start_time, 2),
                    )

        command = self._prepare_command(code, language)

        try:
            exit_code, stdout, stderr = await asyncio.wait_for(
                self._exec_in_container(command, timeout),
                timeout=timeout + 5,
            )
        except asyncio.TimeoutError:
            await self.cleanup()
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

        stdout = truncate_output(stdout, self.max_output_size)
        stderr = truncate_output(stderr, self.max_output_size)

        return ExecutionResult(
            return_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            timeout=False,
            execution_time=round(time.time() - start_time, 2),
        )

    async def _install_dependencies(
        self, requirements: list[str], timeout: int
    ) -> bool:
        if not requirements:
            return True
        install_cmd = get_pip_install_command(requirements)
        if not install_cmd:
            return True
        try:
            exit_code, _, _ = await asyncio.wait_for(
                self._exec_in_container(install_cmd, timeout),
                timeout=timeout + 5,
            )
            return exit_code == 0
        except asyncio.TimeoutError:
            return False

    def _prepare_command(self, code: str, language: str) -> str:
        if language == "python":
            return wrap_python_command(code)
        elif language == "javascript":
            return f"node << 'EOF'\n{code}\nEOF"
        else:
            return code

    async def cleanup(self):
        if self.container is not None:
            try:
                self.container.stop(timeout=5)
                self.container.remove()
            except Exception:
                pass
            self.container = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.cleanup()
