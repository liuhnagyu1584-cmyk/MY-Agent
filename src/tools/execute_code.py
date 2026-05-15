import json
from typing import Optional

from configs.base_config import DOCKER_ENABLED, WORKSPACE_ROOT
from ._sandbox_manager import SandboxManager
from ._sandbox_subprocess import SubprocessSandbox
from ._sandbox_utils import is_safe_file_path, validate_requirements

definition = {
    "type": "function",
    "function": {
        "name": "execute_code",
        "description": (
            "在隔离沙箱中执行代码，支持 Python、JavaScript 和 Bash。"
            "返回 stdout、stderr、return_code 和 execution_time。"
            "Python 代码在隔离虚拟环境中执行，支持自动依赖安装。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的代码片段。与 file_path 二选一。",
                },
                "file_path": {
                    "type": "string",
                    "description": "脚本文件路径（相对于项目根目录）。与 code 二选一。",
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "javascript", "bash"],
                    "description": "编程语言，默认 python。",
                },
                "timeout": {
                    "type": "integer",
                    "description": "执行超时时间（秒），默认 30，范围 1-300。",
                },
                "requirements": {
                    "description": (
                        "Python 依赖列表。支持三种格式：\n"
                        "1. 数组: ['numpy', 'pandas==1.0.0']\n"
                        "2. 字符串: 'requirements.txt' 或 'numpy'\n"
                        "3. null: 自动检测 import 语句中的包"
                    ),
                },
                "env": {
                    "type": "object",
                    "description": "环境变量键值对（仅 Docker 模式支持）。",
                },
                "working_dir": {
                    "type": "string",
                    "description": "工作目录（相对于项目根目录），默认为项目根目录。",
                },
                "max_memory": {
                    "type": "integer",
                    "description": "内存限制（MB），默认 512，范围 128-2048。",
                },
                "max_cpu": {
                    "type": "number",
                    "description": "CPU 限制（核数），默认 1.0，范围 0.1-4.0。",
                },
            },
            "required": [],
            "anyOf": [
                {"required": ["code"]},
                {"required": ["file_path"]},
            ],
        },
    },
}


def _read_file_safe(file_path: str) -> Optional[str]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


async def handler(
    code: Optional[str] = None,
    file_path: Optional[str] = None,
    language: str = "python",
    timeout: int = 30,
    requirements=None,
    env: Optional[dict] = None,
    working_dir: Optional[str] = None,
    max_memory: int = 512,
    max_cpu: float = 1.0,
) -> str:
    code = code or ""
    file_path = file_path or ""
    env = env or {}

    # --- 参数校验 ---
    if not code and not file_path:
        return json.dumps(
            {"error": "必须提供 'code' 或 'file_path' 参数"}, ensure_ascii=False
        )
    if code and file_path:
        return json.dumps(
            {"error": "不能同时指定 'code' 和 'file_path'"}, ensure_ascii=False
        )
    if language not in ("python", "javascript", "bash"):
        return json.dumps(
            {"error": f"不支持的语言: {language}，支持: python, javascript, bash"},
            ensure_ascii=False,
        )

    timeout = max(1, min(int(timeout), 300))
    max_memory = max(128, min(int(max_memory), 2048))
    max_cpu = max(0.1, min(float(max_cpu), 4.0))

    # --- requirements 校验 ---
    valid, req_list = validate_requirements(requirements)
    if not valid:
        return json.dumps(
            {"error": "requirements 格式无效"}, ensure_ascii=False
        )

    # --- 文件读取 ---
    if file_path:
        safe, resolved = is_safe_file_path(file_path, WORKSPACE_ROOT)
        if not safe:
            return json.dumps({"error": resolved}, ensure_ascii=False)
        content = _read_file_safe(resolved)
        if content is None:
            return json.dumps(
                {"error": f"无法读取文件: {file_path}"}, ensure_ascii=False
            )
        code = content

    # --- 沙箱选择 ---
    if DOCKER_ENABLED:
        sandbox = SandboxManager(
            workspace_root=WORKSPACE_ROOT,
            max_timeout=timeout,
            max_memory=max_memory,
            max_cpu=max_cpu,
        )
        if sandbox.error:
            print(f"[沙箱] Docker 不可用，回退到 subprocess 模式: {sandbox.error}")
            sandbox = SubprocessSandbox(
                workspace_root=WORKSPACE_ROOT,
                max_timeout=timeout,
            )
    else:
        sandbox = SubprocessSandbox(
            workspace_root=WORKSPACE_ROOT,
            max_timeout=timeout,
        )

    # --- 执行 ---
    try:
        result = await sandbox.execute_code(
            code=code,
            language=language,
            timeout=timeout,
            requirements=req_list,
        )
    finally:
        await sandbox.cleanup()

    return json.dumps(
        {
            "return_code": result.return_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timeout": result.timeout,
            "execution_time": result.execution_time,
            "error": result.error,
        },
        ensure_ascii=False,
    )
