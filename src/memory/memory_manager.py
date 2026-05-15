import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


SUMMARY_PROMPT = """你是一个会话总结助手。请根据以下对话内容，生成一段简洁的会话摘要。

要求：
1. 提取本次对话的核心主题
2. 记录用户表达过的偏好、习惯或个人信息
3. 记录做出的决定和结论
4. 记录未完成的待办事项
5. 不超过 300 字
6. 使用中文

对话内容：
{context}

会话摘要："""


class MemoryManager:
    def __init__(self, file_path: str, client):
        self.file_path = Path(file_path)
        self.client = client

    def _read_all(self) -> list[dict]:
        if not self.file_path.exists():
            return []
        try:
            return json.loads(self.file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _write_all(self, memories: list[dict]):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(
            json.dumps(memories, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_recent(self, n: int = 5) -> str:
        memories = self._read_all()
        if not memories:
            return ""

        recent = memories[-n:]
        lines = []
        for m in recent:
            ts = m.get("timestamp", "未知时间")
            summary = m.get("summary", "")
            lines.append(f"- [{ts}] {summary}")
        return "\n".join(lines)

    def save(self, summary: str):
        memories = self._read_all()
        memories.append({
            "id": uuid.uuid4().hex[:8],
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "summary": summary,
        })
        self._write_all(memories)

    def clear(self):
        self._write_all([])

    async def summarize(self, context: list[dict]) -> str:
        # 拼接最近用户和助手的消息作为总结素材
        dialogue_parts = []
        for msg in context:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                label = "用户" if role == "user" else "助手"
                # 截断过长的单条消息
                if len(content) > 1000:
                    content = content[:1000] + "..."
                dialogue_parts.append(f"{label}: {content}")

        dialogue_text = "\n".join(dialogue_parts)
        if not dialogue_text.strip():
            return "（无实质对话内容）"

        prompt = SUMMARY_PROMPT.format(context=dialogue_text)

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-v4-pro",
                messages=[{"role": "user", "content": prompt}],
            )
            summary = response.choices[0].message.content or ""
            return summary.strip()
        except Exception as e:
            print(f"[记忆] 摘要生成失败：{e}")
            return "（摘要生成失败）"
