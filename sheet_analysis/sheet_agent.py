from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain.messages import HumanMessage, SystemMessage
from langchain.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from dotenv import load_dotenv
import aiosqlite
import asyncio

from scripts.base_tools import web_search, get_weather
from scripts.utils import load_mcp_config
from scripts.prompts import GOOGLE_SHEET_PROMPT

load_dotenv()

async def get_tools():
    client = MultiServerMCPClient(load_mcp_config("google-sheets", "yahoo-finance"))
    tools = await client.get_tools()
    problematic_tools = ["update_cells"]
    safe_tools = [tool for tool in tools if tool.name not in problematic_tools]

    # print(f"Total tools: {len(tools)}")
    # print(tools)
    return safe_tools 
    

async def main(query: str, thread_id: str):
    model = ChatGoogleGenerativeAI(model="gemini-3-flash-preview")
    tools = await get_tools()
    system_prompt = SystemMessage(GOOGLE_SHEET_PROMPT)
    
    async with aiosqlite.connect("sheet_analysis/memory.db", check_same_thread=False) as conn:
        checkpointer = AsyncSqliteSaver(conn)
        agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
            checkpointer=checkpointer
        )
        
        response = await agent.ainvoke(
            {"messages": [HumanMessage(query)]},
            config={"configurable": {"thread_id": thread_id}}
        )
        
        print(response["messages"][-1].text)
    

if __name__ == "__main__":
    query = "analysis my current portofolio (MSTR 40%, SMH 28%, 005935 22%, SLV 10%) and generate final report in spreadsheet."
    thread_id = "session_04"
    asyncio.run(main(query, thread_id))
    # asyncio.run(get_tools())