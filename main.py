import asyncio
from src.agents.base_agent import BaseAgent


async def main():
    user_input = input("请输入: ")
    agent = BaseAgent()
    result = await agent.run(user_input)
    print(result)
    print("\n" + "=" * 60)


async def main_stream():
    user_input = input("请输入: ")
    agent = BaseAgent()

    async for chunk in agent.run_stream(user_input):
        print(chunk, end="", flush=True)

    print("\n" + "=" * 60)


async def continuous():
    agent = BaseAgent()
    print("输入 /clear or /c 清空历史记忆，输入 /exit or /q 退出")
    while True:
        user_input = input("请输入: ")
        if user_input == "/exit" or user_input == "/q":
            # await agent.save_memory()
            break
        if user_input == "/clear" or user_input == "/c":
            agent.clear_memory()
            continue
        async for chunk in agent.run_stream(user_input):
            print(chunk, end="", flush=True)
        print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(continuous())
