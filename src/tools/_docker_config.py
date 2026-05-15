import os

SANDBOX_IMAGES = {
    "python": os.getenv("SANDBOX_IMAGE_PYTHON", "python:3.11-slim"),
    "javascript": os.getenv("SANDBOX_IMAGE_JAVASCRIPT", "node:20-alpine"),
    "bash": os.getenv("SANDBOX_IMAGE_BASH", "alpine:3.18"),
}

PYTHON_INIT_SCRIPT = """#!/bin/bash
set -e
cd /workspace
python3 -m venv venv
. venv/bin/activate
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
echo "Sandbox initialized"
"""

JAVASCRIPT_INIT_SCRIPT = """#!/bin/sh
cd /workspace
echo "Sandbox initialized"
"""

BASH_INIT_SCRIPT = """#!/bin/sh
cd /workspace
echo "Sandbox initialized"
"""

_INIT_SCRIPTS = {
    "python": PYTHON_INIT_SCRIPT,
    "javascript": JAVASCRIPT_INIT_SCRIPT,
    "bash": BASH_INIT_SCRIPT,
}


def get_init_script(language: str) -> str:
    return _INIT_SCRIPTS.get(language, BASH_INIT_SCRIPT)


def get_resource_config(max_memory: int, max_cpu: float) -> dict:
    return {
        "mem_limit": f"{max_memory}m",
        "memswap_limit": f"{max_memory}m",
        "nano_cpus": int(max_cpu * 1e9),
        "pids_limit": 100,
    }


def wrap_python_command(code: str) -> str:
    return f". /workspace/venv/bin/activate && python3 << 'EOF'\n{code}\nEOF"


def get_pip_install_command(requirements: list[str]) -> str:
    if not requirements:
        return ""
    req_str = " ".join(requirements)
    return f". /workspace/venv/bin/activate && pip install {req_str}"
