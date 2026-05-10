import asyncio
from src.agents.base_agent import BaseAgent


async def main():
    user_input = input("请输入: ")
    agent = BaseAgent()
    result = await agent.run(user_input)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
