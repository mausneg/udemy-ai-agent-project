from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langchain.agents import create_agent
from langchain.messages import HumanMessage, SystemMessage
from langchain.agents.middleware import FilesystemFileSearchMiddleware
from langgraph.checkpoint.sqlite import SqliteSaver
from e2b_code_interpreter import Sandbox
from dotenv import load_dotenv
from pathlib import Path
import sqlite3
import sys
import os
import base64
import pandas as pd
import time
import os

from scripts.prompts import CODE_EXECUTION_PROMPT

load_dotenv()


model = ChatGoogleGenerativeAI(model="gemini-3-flash-preview")
sbx = Sandbox.create(timeout=10*60)

@tool
def upload_file(local_file_name: str):
    """Upload a data file to the E2B sandbox for analysis.
    
    Args:
        local_file_path: Local path to the file (e.g., "IMDB-Movie-Data.csv")
        
    Returns:
        Success message with sandbox_path and dataset_info
    """

    local_file_name = local_file_name.lstrip('/').lstrip('\\')
    local_file_path = f"./data/{local_file_name}"

    if not os.path.exists(local_file_path):
        return f"Error: file not found at {local_file_path}"
    
    with open(local_file_path, "rb") as f:
        sandbox_file = sbx.files.write(f"data/{local_file_name}", f)

    # dataset_info = get_dataset_info(local_file_path)

    return f"File uploaded successfully!\nSandbox path: {sandbox_file.path}"

@tool
def run_python_code(code: str):
    """Execute Python code in E2B sandbox.
    
    Args:
        code: Valid executable Python code. Do not pass anything else otherthan python code.
        
    Returns:
        Execution result
    """
    print('Running code in sandbox....')
    execution = sbx.run_code(code)
    print('Code execution is done!')

    if execution.error:
        return f"Error: {execution.error.name}\nValue: {execution.error.value}"
    
    os.makedirs('images', exist_ok=True)

    output = []
    timestamp = int(time.time())

    output.append(str(execution))

    for idx, result in enumerate(execution.results):
        if result.png:
            filename = f'images/{timestamp}_chart_{idx}.png'
            with open(filename, 'wb') as f:
                f.write(base64.b64decode(result.png))
            
            output.append(f"Chart saved to {filename}")

    return "\n".join(output) if output else "Code executed but no output was returned"

def main(query: str, thread_id: str):
    with sqlite3.connect("code_execution/memory.db", check_same_thread=False) as conn:
        checkpointer = SqliteSaver(conn)
        agent = create_agent(
            model=model,
            tools=[upload_file, run_python_code],
            system_prompt=CODE_EXECUTION_PROMPT,
            checkpointer=checkpointer,
            middleware=[
                FilesystemFileSearchMiddleware(
                    root_path="./data",
                    use_ripgrep=True,
                    max_file_size_mb=1000)
            ]
        )
        response = agent.invoke(
            {"messages": [HumanMessage(query)]},
            config={"configurable": {"thread_id": thread_id}}
        )
        print(response["messages"][-1].text)
        
        sbx.kill()
        
if __name__ == "__main__":
    query = """Analyze the 2024 cash flow and financial performance of Google (Alphabet) and Apple.
        Compute key financial ratios for both companies, including Gross Profit Margin,
        Net Profit Margin, ROA, ROE, Current Ratio, and Debt-to-Equity Ratio.

        Create the following visualizations:
        1. A grouped bar chart comparing Apple vs Google for each financial ratio
        (x-axis: ratio names, y-axis: ratio values, separate bars for Apple and Google).
        2. A comparison table summarizing all calculated ratios side by side.

        Add clear titles, axis labels, legends, and use distinct colors for each company.
        After generating the plots and table, interpret what the visual comparison reveals
        about profitability, efficiency, liquidity, and leverage differences between Apple
        and Google in 2024.
        """
    thread_id = "session_01"
    main(query, thread_id)