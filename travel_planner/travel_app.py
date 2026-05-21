from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.messages import SystemMessage, HumanMessage
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from dotenv import load_dotenv
import os
import asyncio
import aiosqlite

load_dotenv()

from scripts.base_tools import web_search, get_weather
from scripts.prompts import AIRBNB_PROMPT, get_travel_planner_prompt
from scripts.utils import load_mcp_config

model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")


async def get_tools():
    mcp_config = load_mcp_config()
    
    client = MultiServerMCPClient(mcp_config)
    tools = await client.get_tools()
    # print(tools)
    return tools + [web_search, get_weather]


async def main(query, thread_id):
    async with aiosqlite.connect(
        "travel_planner/memory.db", check_same_thread=False
    ) as conn:
        checkpointer = AsyncSqliteSaver(conn=conn)
        await checkpointer.setup()

        tools = await get_tools()
        agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=SystemMessage(get_travel_planner_prompt()),
            checkpointer=checkpointer,
        )
        response = await agent.ainvoke(
            {"messages": [HumanMessage(query)]},
            config={"configurable": {"thread_id": thread_id}},
        )

        print("\nOUTPUT:\n")
        print(response["messages"][-1].text)


if __name__ == "__main__":
    query = "Plan a 1 weeks trip for holiday to Lombok Indonesia. Find a comfortable hotels/villa for 2 adults, check weather, and add the trip to my primary Google Calendar"
    thread_id = "session_1"
    asyncio.run(main(query, thread_id))
