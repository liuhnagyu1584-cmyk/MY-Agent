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


if __name__ == "__main__":
    asyncio.run(main_stream())
