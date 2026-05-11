import os

from ._file_utils import resolve_write_path, is_safe_write_path, get_write_limit

definition = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "将内容写入指定文件。当需要创建新文件、修改代码、保存配置、记录日志时调用。会覆盖已有文件的内容。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要写入的文件绝对路径或相对于项目根目录的路径。",
                },
                "content": {
                    "type": "string",
                    "description": "要写入文件的文本内容。",
                },
            },
            "required": ["file_path", "content"],
        },
    },
}


def handler(file_path: str, content: str) -> str:
    resolved = resolve_write_path(file_path)
    ok, err_msg = is_safe_write_path(resolved)
    if not ok:
        return err_msg

    max_chars = get_write_limit()
    if len(content) > max_chars:
        return (
            f"[错误] 内容过长（{len(content)} 字符），"
            f"超过上限 {max_chars} 字符，请分段写入。"
        )

    dir_path = os.path.dirname(resolved)
    if dir_path and not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            return f"[错误] 无法创建目录 {dir_path}: {e}"

    try:
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        return f"[错误] 写入文件失败: {e}"

    char_count = len(content)
    line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    return f"[成功] 已写入 {resolved}（{line_count} 行，{char_count} 字符）"
