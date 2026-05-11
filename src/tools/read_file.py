import os

from ._file_utils import resolve_path, is_safe_path, get_read_limit

definition = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "读取指定文件的内容。当需要查看代码、配置、日志等文件时调用。支持分段读取（通过 offset 和 limit 参数）。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要读取的文件绝对路径或相对于项目根目录的路径。",
                },
                "offset": {
                    "type": "integer",
                    "description": "可选，从第几行开始读取（从 1 开始计数）。不提供则从文件开头读取。",
                },
                "limit": {
                    "type": "integer",
                    "description": "可选，最多读取多少行。不提供则读取全部。",
                },
            },
            "required": ["file_path"],
        },
    },
}


def handler(file_path: str, offset: int = 1, limit: int | None = None) -> str:
    resolved = resolve_path(file_path)
    ok, err_msg = is_safe_path(resolved)
    if not ok:
        return err_msg

    if not os.path.exists(resolved):
        return f"[错误] 文件不存在: {resolved}"

    if not os.path.isfile(resolved):
        return f"[错误] 路径不是文件: {resolved}"

    try:
        with open(resolved, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        return f"[错误] 无法以 UTF-8 编码读取文件（可能是二进制文件）: {resolved}"
    except Exception as e:
        return f"[错误] 读取文件失败: {e}"

    total_lines = len(lines)
    start = max(offset - 1, 0)

    if start >= total_lines:
        return f"[提示] 文件共 {total_lines} 行，offset={offset} 已超出范围。"

    if limit is not None:
        end = min(start + limit, total_lines)
    else:
        end = total_lines

    selected = lines[start:end]

    max_chars = get_read_limit()
    result = "".join(selected)
    if len(result) > max_chars:
        result = result[:max_chars] + (
            f"\n\n... [已截断，仅显示前 {max_chars} 字符。"
            f"文件共 {total_lines} 行，当前显示第 {start + 1}-{end} 行]"
        )

    header = (
        f"[文件] {resolved}\n"
        f"[行数] 第 {start + 1}-{end} 行 / 共 {total_lines} 行\n"
        f"{'-' * 40}\n"
    )
    return header + result
