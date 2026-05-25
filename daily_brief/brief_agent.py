from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv
import aiosqlite
import asyncio

from scripts.utils import load_mcp_config
from scripts.base_tools import get_weather, web_search
from scripts.prompts import get_assistant_prompt

load_dotenv()

async def get_tools():
    client = MultiServerMCPClient(load_mcp_config())
    tools = await client.get_tools() + [get_weather, web_search]
    
    filter_tools = ["update_cells", "delete_email", "modify_email" "batch_delete_emails", "batch_modify_emails", "delete_label", "delete_filter"]
    used_tools = [tool for tool in tools if tool.name not in filter_tools]
    
    return used_tools 

async def main(query: str, thread_id: str):
    model = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0)
    system_prompt = SystemMessage(get_assistant_prompt())
    tools = await get_tools()
    
    async with aiosqlite.connect("daily_brief/memory.db", check_same_thread=False) as conn:
        checkpointer = AsyncSqliteSaver(conn)
        agent = create_agent(
            model=model,
            system_prompt=system_prompt,
            tools=tools,
            checkpointer=checkpointer
        )
        
        response = await agent.ainvoke(
            {"messages": [HumanMessage(query)]},
            config={"configurable": {"thread_id": thread_id}}
        )
        print(response["messages"][-1].text)
        
if __name__ == "__main__":
    query = """
    Give me my daily brifieng:
    1. Weather for tommorrow
    2. Today's calendar events
    3. Summary of unread emails
    4. Top news headlines in Indoensia
    """
    
    thread_id = "session_02"
    asyncio.run(main(query, thread_id))
        