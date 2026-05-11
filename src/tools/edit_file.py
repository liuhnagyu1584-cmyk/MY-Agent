import os

from ._file_utils import resolve_write_path, is_safe_write_path

definition = {
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": (
            "精确修改文件内容：在文件中查找指定文本（首次匹配），替换为新文本。"
            "只会替换一处，如需替换所有匹配项请设置 replace_all=true。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要编辑的文件绝对路径或相对于项目根目录的路径。",
                },
                "old_string": {
                    "type": "string",
                    "description": "要被替换的原始文本。必须与文件中的内容精确匹配（包括空格和缩进）。",
                },
                "new_string": {
                    "type": "string",
                    "description": "替换后的新文本。",
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "是否替换所有匹配项。默认 false，仅替换首次匹配。",
                },
            },
            "required": ["file_path", "old_string", "new_string"],
        },
    },
}


def _count_occurrences(text: str, target: str) -> int:
    if not target:
        return 0
    count = 0
    idx = 0
    while True:
        idx = text.find(target, idx)
        if idx == -1:
            break
        count += 1
        idx += len(target)
    return count


def _line_col(text: str, pos: int) -> tuple[int, int]:
    line = text[:pos].count("\n") + 1
    prev_nl = text.rfind("\n", 0, pos)
    col = pos - (prev_nl + 1) if prev_nl != -1 else pos + 1
    return line, col


def _context_lines(text: str, target: str) -> str:
    idx = text.find(target)
    if idx == -1:
        return ""
    start = text[:idx]
    end = text[idx + len(target):]

    before_lines = start.split("\n")
    start_line = max(len(before_lines) - 3, 0)
    before_context = "\n".join(before_lines[start_line:])

    end_lines = end.split("\n")
    after_context = "\n".join(end_lines[:3])

    return before_context + " [>>> 替换位置 <<<] " + after_context


def handler(file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    resolved = resolve_write_path(file_path)
    ok, err_msg = is_safe_write_path(resolved)
    if not ok:
        return err_msg

    if not os.path.exists(resolved):
        return f"[错误] 文件不存在: {resolved}"

    if not os.path.isfile(resolved):
        return f"[错误] 路径不是文件: {resolved}"

    try:
        with open(resolved, "r", encoding="utf-8") as f:
            original = f.read()
    except UnicodeDecodeError:
        return f"[错误] 无法以 UTF-8 编码读取文件（可能是二进制文件）: {resolved}"
    except Exception as e:
        return f"[错误] 读取文件失败: {e}"

    if old_string == new_string:
        return "[提示] old_string 与 new_string 相同，无需修改。"

    occurrences = _count_occurrences(original, old_string)
    if occurrences == 0:
        return f"[错误] 未在文件中找到匹配的 old_string。\n提示：请确保 old_string 与文件内容精确匹配（包括空格、缩进、换行）。"

    old_len = len(old_string)
    new_len = len(new_string)
    delta = new_len - old_len

    if replace_all:
        result = original.replace(old_string, new_string)
    else:
        result = original.replace(old_string, new_string, 1)

    try:
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(result)
    except Exception as e:
        return f"[错误] 写入文件失败: {e}"

    old_line_count = original.count("\n") + 1
    new_line_count = result.count("\n") + 1
    context = _context_lines(original, old_string)

    header = (
        f"[成功] 已编辑 {resolved}\n"
        f"[匹配] 共 {occurrences} 处匹配，已替换 {'全部' if replace_all else '首处'}\n"
        f"[差异] 替换 {old_len} → {new_len} 字符（{delta:+d}）\n"
        f"[行数] {old_line_count} → {new_line_count} 行\n"
        f"{'-' * 40}\n"
    )
    if context:
        header += f"[变更上下文]\n{context}\n"
    if not replace_all and occurrences > 1:
        header += f"\n[提示] 还有 {occurrences - 1} 处匹配未修改。如需全部替换请设置 replace_all=true。\n"

    return header
