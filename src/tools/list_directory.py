import os
import fnmatch
from datetime import datetime

from ._file_utils import resolve_path, FULL_ACCESS, ALLOW_UNSAFE, PROTECTED_DIRS

MAX_ITEMS = 200 # 最大列出项数
MAX_RECURSIVE_DEPTH = 3 # 最大递归深度

definition = {
    "type": "function",
    "function": {
        "name": "list_directory",
        "description": "浏览目录内容，列出文件和子目录。支持递归和 glob 模式匹配。当需要了解项目结构、查找文件时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "dir_path": {
                    "type": "string",
                    "description": "要浏览的目录路径（绝对路径或相对于项目根目录）。不提供则默认为项目根目录。",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "是否递归列出子目录。默认 false，最大深度 3 层。",
                },
                "pattern": {
                    "type": "string",
                    "description": "可选，glob 模式匹配文件名，如 '*.py' 或 'test_*'。不提供则列出所有文件。",
                },
            },
            "required": [],
        },
    },
}


def _format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def _is_protected_dir(name: str) -> bool:
    """检查目录是否为受保护目录"""
    if FULL_ACCESS or ALLOW_UNSAFE:
        return name in {".git", ".venv", "__pycache__"}
    return name in PROTECTED_DIRS


def _matches_pattern(name: str, pattern: str | None) -> bool:
    """检查文件名是否匹配模式"""
    if not pattern:
        return True
    return fnmatch.fnmatch(name, pattern)


def _list_recursive(
    root: str, recursive: bool, pattern: str | None, depth: int
) -> tuple[list[str], int, int]:
    """递归列出目录内容"""
    file_lines: list[str] = []
    dir_lines: list[str] = []
    file_count = 0
    dir_count = 0

    try:
        entries = sorted(os.scandir(root), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return [f"  [无权限] {root}"], 0, 0
    except Exception as e:
        return [f"  [错误] {root}: {e}"], 0, 0

    for entry in entries:
        if file_count + dir_count >= MAX_ITEMS:
            file_lines.append(f"  ... [已达到最大显示数量 {MAX_ITEMS}，结果已截断]")
            break

        name = entry.name
        if _is_protected_dir(name):
            continue

        try:
            is_dir = entry.is_dir()
            is_file = entry.is_file()
        except OSError:
            continue

        if is_dir:
            if not _matches_pattern(name, pattern):
                continue
            dir_count += 1
            rel_path = os.path.relpath(entry.path, root) if recursive else name
            prefix = "  " * depth
            dir_lines.append(f"{prefix}[DIR]{rel_path}/")
            if recursive and depth < MAX_RECURSIVE_DEPTH:
                sub_lines, sub_files, sub_dirs = _list_recursive(
                    entry.path, True, pattern, depth + 1
                )
                dir_lines.extend(sub_lines)
                file_count += sub_files
                dir_count += sub_dirs

        elif is_file:
            if not _matches_pattern(name, pattern):
                continue
            file_count += 1
            try:
                size = entry.stat().st_size
                mtime = datetime.fromtimestamp(entry.stat().st_mtime).strftime(
                    "%Y-%m-%d %H:%M"
                )
            except OSError:
                size = 0
                mtime = "----"
            prefix = "  " * depth
            file_lines.append(f"{prefix}[FILE]{name} ({_format_size(size)}, {mtime})")

    return file_lines + dir_lines, file_count, dir_count


def handler(
    dir_path: str | None = None, recursive: bool = False, pattern: str | None = None
) -> str:
    if dir_path:
        resolved = resolve_path(dir_path)
    else:
        from configs.base_config import WORKSPACE_ROOT

        resolved = WORKSPACE_ROOT or os.getcwd()

    if not os.path.exists(resolved):
        return f"[错误] 目录不存在: {resolved}"

    if not os.path.isdir(resolved):
        return f"[错误] 路径不是目录: {resolved}"

    basename = os.path.basename(resolved)
    if basename in PROTECTED_DIRS and not (FULL_ACCESS or ALLOW_UNSAFE):
        return f"[安全拒绝] 禁止浏览受保护的目录: {basename}"

    output_lines, file_count, dir_count = _list_recursive(
        resolved, recursive, pattern, 0
    )

    header = (
        f"[目录] {resolved}\n"
        f"[统计] 共 {file_count + dir_count} 个项目（{file_count} 文件, {dir_count} 目录）\n"
    )
    if pattern:
        header += f"[过滤] pattern: {pattern}\n"
    header += "-" * 40 + "\n"

    return header + "\n".join(output_lines) if output_lines else header + "(空目录)"
