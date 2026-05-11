import os
from pathlib import Path

from configs.base_config import FULL_ACCESS, WORKSPACE_ROOT, ALLOW_UNSAFE

# 安全操作黑名单 （二进制/编译文件类型）
BLACKLIST_EXTENSIONS = {".exe", ".dll", ".so", ".pyc", ".pyd", ".bin", ".dat"}
# 受保护的文件名黑名单
PROTECTED_FILENAMES = {".env", ".gitignore"}
# 受保护的目录黑名单
PROTECTED_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".idea", ".vscode"}

MAX_READ_CHARS_DEFAULT = 8000 # 读取字符限制
MAX_READ_CHARS_UNSAFE = 50000 # 读取字符限制（不安全模式）
MAX_WRITE_CHARS_DEFAULT = 50000 # 写入字符限制
MAX_WRITE_CHARS_UNSAFE = 500000 # 写入字符限制（不安全模式）


def _inside_root(resolved: str) -> bool:
    """检查路径是否在工作区范围内"""
    if not WORKSPACE_ROOT:
        return True
    root = os.path.normpath(WORKSPACE_ROOT).rstrip(os.sep) + os.sep
    target = os.path.normpath(resolved).rstrip(os.sep) + os.sep
    return target.startswith(root)


def resolve_path(path: str) -> str:
    """将路径转换为绝对路径"""
    path = os.path.expanduser(path)
    if os.path.isabs(path):
        return os.path.normpath(path)
    root = WORKSPACE_ROOT or os.getcwd()
    return os.path.normpath(os.path.join(root, path))


def resolve_write_path(path: str) -> str:
    """将写入路径转换为绝对路径"""
    path = os.path.expanduser(path)
    if os.path.isabs(path):
        return os.path.normpath(path)
    root = WORKSPACE_ROOT or os.getcwd()
    return os.path.normpath(os.path.join(root, path))


def is_safe_path(path: str) -> tuple[bool, str]:
    """检查路径是否安全"""
    if FULL_ACCESS:
        return (True, "")

    if not _inside_root(path):
        return (False, f"[安全拒绝] 路径不在工作区范围内: {path}")

    if ALLOW_UNSAFE:
        return (True, "")

    ext = os.path.splitext(path)[1].lower()
    if ext in BLACKLIST_EXTENSIONS:
        return (False, f"[安全拒绝] 禁止操作二进制/编译文件类型 ({ext}): {path}")

    basename = os.path.basename(path)
    if basename in PROTECTED_FILENAMES:
        return (False, f"[安全拒绝] 禁止操作受保护的文件: {basename}")

    path_obj = Path(path)
    for part in path_obj.parts:
        if part in PROTECTED_DIRS:
            return (False, f"[安全拒绝] 禁止操作受保护目录内的文件: {part}")

    return (True, "")


def is_safe_write_path(path: str) -> tuple[bool, str]:
    """检查写入路径是否安全"""
    ok, msg = is_safe_path(path)
    if not ok:
        return (ok, msg)
    if FULL_ACCESS:
        return (True, "")
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent) and not ALLOW_UNSAFE:
        pass
    return (True, "")


def is_safe_delete_path(path: str) -> tuple[bool, str]:
    """检查删除路径是否安全"""
    ok, msg = is_safe_path(path)
    if not ok:
        return (ok, msg)
    if FULL_ACCESS:
        return (True, "")
    basename = os.path.basename(path)
    if basename in PROTECTED_FILENAMES:
        return (False, f"[安全拒绝] 禁止删除受保护的文件: {basename}")
    return (True, "")


def get_read_limit() -> int:
    """获取读取字符限制"""
    if FULL_ACCESS or ALLOW_UNSAFE:
        return MAX_READ_CHARS_UNSAFE
    return MAX_READ_CHARS_DEFAULT


def get_write_limit() -> int:
    """获取写入字符限制"""
    if FULL_ACCESS or ALLOW_UNSAFE:
        return MAX_WRITE_CHARS_UNSAFE
    return MAX_WRITE_CHARS_DEFAULT
