import os

from ._file_utils import resolve_path, is_safe_delete_path

definition = {
    "type": "function",
    "function": {
        "name": "delete_file",
        "description": "删除指定文件。操作不可逆，请确认文件不再需要后再调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要删除的文件绝对路径或相对于项目根目录的路径。",
                },
            },
            "required": ["file_path"],
        },
    },
}


def handler(file_path: str) -> str:
    resolved = resolve_path(file_path)
    ok, err_msg = is_safe_delete_path(resolved)
    if not ok:
        return err_msg

    if not os.path.exists(resolved):
        return f"[错误] 文件不存在: {resolved}"

    if not os.path.isfile(resolved):
        return f"[错误] 路径不是文件: {resolved}"

    try:
        os.remove(resolved)
    except Exception as e:
        return f"[错误] 删除文件失败: {e}"

    return f"[成功] 已删除 {resolved}"
