from pathlib import Path

PPT_SYSTEM_PATH = Path(__file__).parent / "system_prompt.md"


def get_system_prompt():
    return PPT_SYSTEM_PATH.read_text(encoding="utf-8")
