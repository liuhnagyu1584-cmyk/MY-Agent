import inspect
import json
from types import SimpleNamespace
from configs.base_config import (
    MAX_ITERATIONS,
    MEMORY_FILE,
    MEMORY_MAX_LOAD,
    MODEL_API_KEY,
    MODEL_BASE_URL,
    MODEL_NAME,
)
from openai import AsyncOpenAI
from src.memory import MemoryManager
from src.prompts.system_prompt import get_system_prompt
from src.tools import TOOL_DEFINITIONS, TOOL_HANDLERS


class BaseAgent:
    def __init__(self):
        api_key = MODEL_API_KEY
        base_url = MODEL_BASE_URL

        self.system_prompt = get_system_prompt()
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.context: list = [
            {"role": "system", "content": self.system_prompt},
        ]

        self.memory_manager = MemoryManager(MEMORY_FILE, self.client)
        self._load_memory(MEMORY_MAX_LOAD)

    async def run(
        self,
        user_input: str,
    ):
        self.context.append({"role": "user", "content": user_input})

        print("正在思考...", "==" * 20)

        for _ in range(MAX_ITERATIONS):
            print(f"第 {_ + 1} 次迭代")
            message, error = await self._call_llm(self.context)
            if error:
                return error
            assert message is not None

            if message.tool_calls:
                self._append_assistant_with_tools(self.context, message)
                results = await self._execute_tools(message.tool_calls)
                self._append_tool_results(self.context, message.tool_calls, results)
                continue

            print("上下文: ", self.context, "=" * 20)
            self.context.append({"role": "assistant", "content": message.content})
            return message.content

        return "已达到最大迭代次数，请尝试简化你的问题。"

    async def run_stream(self, user_input: str):
        self.context.append({"role": "user", "content": user_input})

        print("正在思考...", "==" * 20)

        for _ in range(MAX_ITERATIONS):
            print(f"第 {_ + 1} 次迭代")
            response, error = await self._call_llm_stream(self.context)
            if error:
                yield error
                return
            assert response is not None

            tool_calls_acc: dict[int, dict] = {}  # 记录每个工具调用的索引和内容
            content_parts: list[str] = []  # 记录每个delta的内容
            reasoning_parts: list[str] = []  # 记录每个delta的推理内容

            async for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                if delta.content:
                    content_parts.append(delta.content)
                    yield delta.content

                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                    reasoning_parts.append(reasoning)

                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        func = tc_delta.function
                        if func is None:
                            continue
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {
                                "id": tc_delta.id or "",
                                "function": {
                                    "name": func.name or "",
                                    "arguments": func.arguments or "",
                                },
                            }
                        else:
                            if tc_delta.id:
                                tool_calls_acc[idx]["id"] = tc_delta.id
                            if func.name:
                                tool_calls_acc[idx]["function"]["name"] += func.name
                            if func.arguments:
                                tool_calls_acc[idx]["function"][
                                    "arguments"
                                ] += func.arguments

            if tool_calls_acc:
                tc_objects = [
                    SimpleNamespace(
                        id=tc["id"],
                        function=SimpleNamespace(
                            name=tc["function"]["name"],
                            arguments=tc["function"]["arguments"],
                        ),
                    )
                    for tc in tool_calls_acc.values()
                ]
                message_like = SimpleNamespace(
                    content="".join(content_parts),
                    tool_calls=tc_objects,
                    reasoning_content="".join(reasoning_parts) or None,
                )
                self._append_assistant_with_tools(self.context, message_like)
                results = await self._execute_tools(tc_objects)
                self._append_tool_results(self.context, tc_objects, results)
                continue

            self.context.append(
                {"role": "assistant", "content": "".join(content_parts)}
            )
            return

        yield "已达到最大迭代次数，请尝试简化你的问题。"

    async def _call_llm(self, context: list):
        try:
            response = await self.client.chat.completions.create(
                model=MODEL_NAME, messages=context, tools=TOOL_DEFINITIONS
            )
            return response.choices[0].message, None
        except Exception as e:
            print(f"[错误] API 调用失败：{e}")
            return None, f"API 调用失败：{e}"

    async def _call_llm_stream(self, context: list):
        try:
            response = await self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=context,
                tools=TOOL_DEFINITIONS,
                stream=True,
            )
            return response, None
        except Exception as e:
            print(f"[错误] API 调用失败：{e}")
            return None, f"API 调用失败：{e}"

    def _append_assistant_with_tools(self, context: list[dict], message):
        """
        追加助手消息到上下文，包含工具调用。
        """

        tool_calls_data = []

        for tc in message.tool_calls:
            tool_calls_data.append(
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
            )

        entry = {
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": tool_calls_data,
        }
        if hasattr(message, "reasoning_content") and message.reasoning_content:
            entry["reasoning_content"] = message.reasoning_content
        context.append(entry)

    async def _execute_tools(self, tool_calls: list):
        """
        执行工具调用。
        """
        results = []
        for tc in tool_calls:
            func_name = tc.function.name
            handler = TOOL_HANDLERS[func_name]

            if handler is None:
                results.append(f"[错误] 未知工具：{func_name}")
                continue

            try:
                args = json.loads(tc.function.arguments)
                print(f"🧰 调用工具: {func_name} 📖 工具参数: {args[:50]}...", "=" * 20)
                if inspect.iscoroutinefunction(handler):
                    result = await handler(**args)
                else:
                    result = handler(**args)
                results.append(result)
            except Exception as e:
                results.append(f"[错误] 工具 {func_name} 执行失败：{e}")

        return results

    def _append_tool_results(
        self, context: list[dict], tool_calls: list, results: list
    ):
        """
        追加工具调用结果到上下文。
        """
        for tc, result in zip(tool_calls, results):
            context.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    def _load_memory(self, n: int):
        summary = self.memory_manager.load_recent(n)
        if summary:
            self.context.append({
                "role": "system",
                "content": f"[历史记忆]\n以下是你在之前会话中与用户的互动摘要，可在对话中参考：\n{summary}",
            })
            print(f"[记忆] 已加载最近 {n} 条历史记忆")

    async def save_memory(self):
        print("[记忆] 正在总结本次会话...")
        summary = await self.memory_manager.summarize(self.context)
        self.memory_manager.save(summary)
        print(f"[记忆] 已保存，摘要：{summary[:100]}...")

    def clear_memory(self):
        self.memory_manager.clear()
        print("[记忆] 所有历史记忆已清空")
