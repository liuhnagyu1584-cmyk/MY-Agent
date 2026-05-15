import ast
import json
import os
from typing import Optional


STDLIB_MODULES = frozenset({
    "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio",
    "asyncore", "atexit", "audioop", "base64", "bdb", "binascii", "binhex",
    "bisect", "builtins", "bz2", "calendar", "cgi", "cgitb", "chunk", "cmath",
    "cmd", "code", "codecs", "codeop", "collections", "colorsys", "compileall",
    "concurrent", "configparser", "contextlib", "contextvars", "copy",
    "copyreg", "cProfile", "crypt", "csv", "ctypes", "curses", "dataclasses",
    "datetime", "dbm", "decimal", "difflib", "dis", "distutils", "doctest",
    "email", "encodings", "enum", "errno", "faulthandler", "fcntl",
    "filecmp", "fileinput", "fnmatch", "formatter", "fractions", "ftplib",
    "functools", "gc", "getopt", "getpass", "gettext", "glob", "grp",
    "gzip", "hashlib", "heapq", "hmac", "html", "http", "idlelib", "imaplib",
    "imghdr", "imp", "importlib", "inspect", "io", "ipaddress", "itertools",
    "json", "keyword", "lib2to3", "linecache", "locale", "logging", "lzma",
    "mailbox", "mailcap", "marshal", "math", "mimetypes", "mmap",
    "modulefinder", "multiprocessing", "netrc", "nis", "nntplib", "numbers",
    "operator", "optparse", "os", "ossaudiodev", "parser", "pathlib",
    "pdb", "pickle", "pickletools", "pipes", "pkgutil", "platform",
    "plistlib", "poplib", "posix", "posixpath", "pprint", "profile",
    "pstats", "pty", "pwd", "py_compile", "pyclbr", "pydoc", "queue",
    "quopri", "random", "re", "readline", "reprlib", "resource", "rlcompleter",
    "runpy", "sched", "secrets", "select", "selectors", "shelve", "shlex",
    "shutil", "signal", "site", "smtpd", "smtplib", "sndhdr", "socket",
    "socketserver", "spwd", "sqlite3", "ssl", "stat", "statistics", "string",
    "stringprep", "struct", "subprocess", "sunau", "symtable", "sys",
    "sysconfig", "syslog", "tabnanny", "tarfile", "telnetlib", "tempfile",
    "termios", "test", "textwrap", "threading", "time", "timeit", "tkinter",
    "token", "tokenize", "trace", "traceback", "tracemalloc", "tty",
    "turtle", "turtledemo", "types", "typing", "unicodedata", "unittest",
    "urllib", "uu", "uuid", "venv", "warnings", "wave", "weakref",
    "webbrowser", "winreg", "winsound", "wsgiref", "xdrlib", "xml",
    "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib",
})


def resolve_sandbox_path(path: str, workspace_root: str) -> tuple[bool, str]:
    if not path:
        return (False, "")
    try:
        if os.path.isabs(path):
            resolved = os.path.normpath(path)
        else:
            resolved = os.path.normpath(os.path.join(workspace_root, path))
        rel = os.path.relpath(resolved, workspace_root)
        if rel.startswith("..") or os.path.isabs(rel):
            return (False, "")
        if os.path.islink(resolved):
            return (False, "")
        return (True, resolved)
    except (ValueError, OSError):
        return (False, "")


def is_safe_file_path(file_path: str, workspace_root: str) -> tuple[bool, str]:
    valid, resolved = resolve_sandbox_path(file_path, workspace_root)
    if not valid:
        return (False, f"[安全拒绝] 路径不在沙箱范围内: {file_path}")
    if not os.path.exists(resolved):
        return (False, f"[错误] 文件不存在: {file_path}")
    if not os.path.isfile(resolved):
        return (False, f"[错误] 不是文件: {file_path}")
    return (True, resolved)


def extract_imports(code: str) -> list[str]:
    packages: set[str] = set()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in STDLIB_MODULES:
                    packages.add(top)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None and node.level == 0:
                top = node.module.split(".")[0]
                if top not in STDLIB_MODULES:
                    packages.add(top)
    return sorted(packages)


def validate_requirements(requirements) -> tuple[bool, Optional[list[str]]]:
    if requirements is None:
        return (True, None)
    if isinstance(requirements, list):
        return (True, requirements)
    if isinstance(requirements, str):
        stripped = requirements.strip()
        if stripped.endswith(".txt"):
            return (True, [stripped])
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return (True, parsed)
            except json.JSONDecodeError:
                pass
        return (True, [stripped])
    return (False, None)


def check_file_size(file_path: str, max_size: int) -> tuple[bool, str]:
    if not os.path.exists(file_path):
        return (False, f"[错误] 文件不存在: {file_path}")
    size = os.path.getsize(file_path)
    if size > max_size:
        return (False, f"[错误] 文件过大: {size} bytes (限制 {max_size} bytes)")
    return (True, "")


def truncate_output(text: str, max_size: int) -> str:
    if len(text) <= max_size:
        return text
    return text[:max_size] + f"\n... (已截断, 共 {len(text)} bytes)"
