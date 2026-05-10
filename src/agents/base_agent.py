import inspect
import json
from configs.base_config import (
    MAX_ITERATIONS,
    MODEL_API_KEY,
    MODEL_BASE_URL,
    MODEL_NAME,
)
from openai import AsyncOpenAI
from src.prompts.system_prompt import get_system_prompt
from src.tools import TOOL_DEFINITIONS, TOOL_HANDLERS


class BaseAgent:
    def __init__(self):
        api_key = MODEL_API_KEY
        base_url = MODEL_BASE_URL

        self.system_prompt = get_system_prompt()
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def run(
        self,
        user_input: str,
    ):
        context: list = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input},
        ]

        print("正在思考...", "==" * 20)

        for _ in range(MAX_ITERATIONS):
            print(f"第 {_ + 1} 次迭代")
            try:
                response = await self.client.chat.completions.create(
                    model=MODEL_NAME, messages=context, tools=TOOL_DEFINITIONS
                )
            except Exception as e:
                print(f"[错误] API 调用失败：{e}")
                return f"API 调用失败：{e}"

            message = response.choices[0].message

            if message.tool_calls:
                self._append_assistant_with_tools(context, message)
                results = await self._execute_tools(message.tool_calls)
                self._append_tool_results(context, message.tool_calls, results)
                continue

            print("上下文: ", context, "=" * 20)
            return message.content

        return "已达到最大迭代次数，请尝试简化你的问题。"

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
            print("调用工具:", func_name)
            handler = TOOL_HANDLERS[func_name]

            if handler is None:
                results.append(f"[错误] 未知工具：{func_name}")
                continue

            try:
                args = json.loads(tc.function.arguments)
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
