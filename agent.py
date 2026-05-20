import os
from dotenv import load_dotenv
load_dotenv(override=True)
import asyncio
from openai import AsyncOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import json
from config import get_github_model
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class YouTubeResearchReport(BaseModel):
    topic: str = Field(description="The main topic of the research")
    summary: str = Field(description="Detailed summary of the video transcripts found")
    key_takeaways: list[str] = Field(description="A bulleted list of 3-5 crucial facts")
    source_urls: list[str] = Field(description="List of YouTube URLs used in the research")

    channel_subscribers: Optional[str] = Field(default="N/A", description="Formatted subscriber count (e.g., '1.2M' or raw number)")
    like_count: Optional[str] = Field(default="N/A", description="Formatted like count")
    comment_count: Optional[str] = Field(default="N/A", description="Formatted comment count")

def format_for_openai(mcp_tools) -> list:
    """
    Translates MCP tool schema to OpenAI JSON format.
    """
    formatted_tools = []
    
    # Check if we have tools to format
    if not mcp_tools or not hasattr(mcp_tools, 'tools'):
        return formatted_tools
        
    for tool in mcp_tools.tools:
        # 1. Build the base structure OpenAI expects
        openai_tool = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
            }
        }
        
        # 2. Map the input schema if it exists
        if hasattr(tool, 'inputSchema') and tool.inputSchema:
            openai_tool["function"]["parameters"] = tool.inputSchema
        else:
            # If no parameters, provide an empty schema
            openai_tool["function"]["parameters"] = {
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
            
        formatted_tools.append(openai_tool)
        
    return formatted_tools

async def run_youtube_agent(user_query: str):
    # 1. Define how to connect to your MCP server

    _, custom_client = get_github_model()
    MODEL_STRING = "gpt-4o"

    server_params = StdioServerParameters(
        command="python",
        args=["youtube_mcp_server.py"],
    )

    current_time = datetime.now().strftime("%A, %B %d, %Y")

    # 2. Connect the MCP Client
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Fetch tools from the MCP server
            mcp_tools = await session.list_tools()
            
            # (Format mcp_tools into OpenAI's strict JSON schema here)
            formatted_tools = format_for_openai(mcp_tools)
            
            # 3. Initialize the OpenAI Agent
            # client = AsyncOpenAI()
            
            messages = [
                {
                    "role": "system", 
                    "content": (
                        f"You are a rigorous YouTube research agent. Today's date is {current_time}.\n"
                        "You MUST follow this exact workflow:\n"
                        "1. Use 'search_youtube' to find a highly relevant and recent video.\n"
                        "2. Extract the video_id from the search results.\n"
                        "3. Use 'get_video_details' with that video_id to fetch the likes, comments, and subscriber count.\n" 
                        "4. Use 'get_video_transcript' to read the video's content.\n"
                        "5. Analyze the transcript to answer the user's question accurately.\n"
                        "CRITICAL: Do NOT stop researching or output your final answer until you have successfully fetched the transcript and video details."
                    )
                },
                {"role": "user", "content": user_query}
            ]
            
            print("Agent is thinking...")
            
            while True:
                response = await custom_client.chat.completions.create(
                    model=MODEL_STRING,
                    messages=messages,
                    tools=formatted_tools
                )
                
                message = response.choices[0].message
                
                # If the AI wants to use a tool, execute it!
                if message.tool_calls:
                    messages.append(message) # Add AI's tool request to history
                    
                    for tool_call in message.tool_calls:
                        print(f"Calling tool: {tool_call.function.name}...")
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        
                        tool_result = await session.call_tool(tool_name, tool_args)
                        
                        # Feed the tool's output back to the LLM
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": str(tool_result.content[0].text) 
                        })
                else:
                    # If there are no tool calls, the AI has finished its research! Break the loop.
                    break
            
            # --- PYDANTIC STRUCTURED OUTPUT ---
            # Now that the research is done, force the LLM to format the history into our Pydantic model
            print("Formatting final report...")
            messages.append({
                "role": "user", 
                "content": "Compile your findings into the final research report schema."
            })
            
            final_response = await custom_client.beta.chat.completions.parse(
                model=MODEL_STRING,
                messages=messages,
                response_format=YouTubeResearchReport
            )
            
            return final_response.choices[0].message.parsed

if __name__ == "__main__":
    report = asyncio.run(run_youtube_agent("Find a recent video about IPL and summarize its transcript."))
    print(f"\n🚀 TOPIC: {report.topic}")
    print(f"📝 SUMMARY: {report.summary}")
    print("🔑 KEY TAKEAWAYS:")
    for takeaway in report.key_takeaways:
        print(f"  - {takeaway}")
    print(f"🔗 SOURCES: {report.source_urls}")