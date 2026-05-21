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
from typing import Optional, Type
import sys

class YouTubeResearchReport(BaseModel):
    topic: str = Field(description="The main topic of the research")
    summary: str = Field(description="Detailed summary of the video transcripts found")
    key_takeaways: list[str] = Field(description="A bulleted list of 3-5 crucial facts")
    source_urls: list[str] = Field(description="List of YouTube URLs used in the research")

    channel_subscribers: Optional[str] = Field(default="N/A", description="Formatted subscriber count (e.g., '1.2M' or raw number)")
    like_count: Optional[str] = Field(default="N/A", description="Formatted like count")
    comment_count: Optional[str] = Field(default="N/A", description="Formatted comment count")
    audience_sentiment: Optional[str] = Field(
        default="Not analyzed", 
        description="A 1-2 sentence summary of the audience's reaction based on the comments (e.g., 'Overwhelmingly positive, users praised the clarity' or 'Skeptical, many users pointed out a flaw')."
    )

class ChannelDeepDiveReport(BaseModel):
    channel_name: str = Field(description="The official name of the channel")
    overarching_theme: str = Field(description="A comprehensive summary of the channel's current focus, narrative, or bias based on their recent videos")
    recent_topics: list[str] = Field(description="A bulleted list of the specific topics covered in the analyzed videos")
    target_audience: str = Field(description="Who this channel appears to be creating content for")


custom_client = get_github_model()
MODEL_STRING = "gpt-4.1-nano" 
current_time = datetime.now().strftime("%A, %B %d, %Y")
# 1. Define how to connect to your MCP server
server_params = StdioServerParameters(
    command=sys.executable,
    args=["youtube_mcp_server.py"],
)

async def execute_agent_loop(
    custom_client, 
    session, 
    model_string: str, 
    messages: list, 
    formatted_tools: list, 
    response_schema: Type[BaseModel]
):
    """A generic engine that handles the tool-calling loop and final Pydantic parsing."""
    
    # 1. The Execution Loop
    while True:
        response = await custom_client.chat.completions.create(
            model=model_string,
            messages=messages,
            tools=formatted_tools
        )
        
        message = response.choices[0].message
        
        if message.tool_calls:
            messages.append(message) 
            for tool_call in message.tool_calls:
                print(f"⚙️ Executing tool: {tool_call.function.name}...")
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                tool_result = await session.call_tool(tool_name, tool_args)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(tool_result.content[0].text) 
                })
        else:
            break
            
    # 2. The Pydantic Parse
    print("✨ Formatting final structured report...")
    messages.append({
        "role": "user", 
        "content": f"Compile your findings into the {response_schema.__name__} schema."
    })
    
    final_response = await custom_client.beta.chat.completions.parse(
        model=model_string, 
        messages=messages,
        response_format=response_schema
    )
    
    return final_response.choices[0].message.parsed

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
                        "6. Use 'get_video_comments' to analyze the transcript and comments to answer the user's question accurately.\n"
                        "CRITICAL: Do NOT stop researching or output your final answer until you have successfully fetched the transcript and video details."
                    )
                },
                {"role": "user", "content": user_query}
            ]
            
            print("Agent is thinking...")

            return await execute_agent_loop(
                custom_client, session, MODEL_STRING, messages, formatted_tools, YouTubeResearchReport
            )

async def run_channel_agent(channel_query: str):

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            formatted_tools = format_for_openai(await session.list_tools())
            
            messages = [
                {
                    "role": "system", 
                    "content": (
                        f"You are a YouTube Channel Analyst. Today's date is {current_time}.\n"
                        "You MUST follow this exact workflow:\n"
                        "1. Use 'get_channel_latest_videos' to find the channel and get their 3 most recent video IDs.\n"
                        "2. Use 'get_video_transcript' on EACH of those 3 video IDs to read their content.\n"
                        "3. Analyze all the transcripts together to determine the channel's overarching narrative, themes, and target audience.\n"
                        "CRITICAL: You must read the transcripts of multiple videos before outputting your final report."
                    )
                },
                {"role": "user", "content": f"Do a deep dive on this channel: {channel_query}"}
            ]
            
            print(f"📺 Starting Channel Deep Dive for: {channel_query}...")
            # Pass the generic loop the ChannelDeepDiveReport schema
            return await execute_agent_loop(
                custom_client, session, MODEL_STRING, messages, formatted_tools, ChannelDeepDiveReport
            )
            

if __name__ == "__main__":
    report = asyncio.run(run_youtube_agent("Find a recent video about IPL and summarize its transcript."))
    print(f"\n🚀 TOPIC: {report.topic}")
    print(f"📝 SUMMARY: {report.summary}")
    print("🔑 KEY TAKEAWAYS:")
    for takeaway in report.key_takeaways:
        print(f"  - {takeaway}")
    print(f"🔗 SOURCES: {report.source_urls}")