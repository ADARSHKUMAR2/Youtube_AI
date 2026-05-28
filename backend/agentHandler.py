import datetime
import os
import sys
from dotenv import load_dotenv
from datetime import datetime as dt 
from duckduckgo_search import DDGS
from openai import AsyncOpenAI
from agents import Agent, Runner, function_tool
from agents.mcp.server import MCPServerStdio
from mcp.client.stdio import StdioServerParameters
from backend.config import Config
from schemas.schema import YouTubeResearchReport, ChannelDeepDiveReport, ClickbaitExposureReport
from pydantic import BaseModel
from typing import Type
from litellm import completion

load_dotenv(override=True)

# --- 2. Configuration ---
current_time = dt.now().strftime("%A, %B %d, %Y")

@function_tool
def search_web(query: str) -> str:
    """
    CRITICAL: Use this tool to search the internet and verify any factual claims, 
    drama, or statistics mentioned in the YouTube video. Do not trust the video blindly.
    """
    print(f"🌐 Fact-Checking on the web: {query}")
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            formatted_results = "\n".join([f"- {r['title']}: {r['body']}" for r in results])
            return formatted_results if formatted_results else "No results found."
    except Exception as e:
        return f"Web search failed: {str(e)}"

raw_youtube_params = {
    "command": sys.executable,
    "args": ["backend/youtube_mcp_server.py"],
    "env": dict(os.environ)
}

# --- 4. The Master Orchestrator ---
async def run_modern_agent(name: str, instructions: str, query: str, response_schema: Type[BaseModel]):
    
    youtube_mcp_server = MCPServerStdio(
    name="YouTube_MCP",  
    params=raw_youtube_params,
    client_session_timeout_seconds=60
    )

    async with youtube_mcp_server:
    # Initialize the modern Agent with BOTH local tools and MCP servers
        agent = Agent(
            name=name,
            model=Config.openai_model,
            instructions=instructions,   
            tools=[search_web],         
            mcp_servers=[youtube_mcp_server] 
        )
        print(f"🤖 {name} is thinking (via native OpenAI MCP)...")
        result = await Runner.run(
                agent,
                query,
                max_turns=15
            )
    
    print(f"✨ Formatting final report for {name}...")

    formatted = completion(
        model=Config.openai_model,
        api_key=Config.openai_key,
        response_format=response_schema,
        messages=[
            {
                "role": "system",
                "content": f"""
                Convert the agent findings into STRICT valid JSON.

                    Follow this schema exactly:

                    {response_schema.model_json_schema()}

                    Rules:
                    - Output ONLY valid JSON
                    - No markdown
                    - No explanations
                    - No code blocks
                    """
            },
            {
                "role": "user",
                "content": f"Here is the raw content:\n\n{result.final_output}"
            }
        ]
    )

    print("Formatted Output from LLM : completions ")
    raw_json_string = formatted.choices[0].message.content
    print("Formatted Output from LLM : completions ")
    print(raw_json_string)
    
    # 2. Convert the raw JSON string back into your Pydantic object
    final_parsed_object = response_schema.model_validate_json(raw_json_string)
    
    return final_parsed_object
    
# --- 5. Orchestrators ---

async def run_youtube_agent(user_query: str):
    instructions = (
        f"You are a rigorous YouTube research agent. Today's date is {current_time}.\n"
        "CRITICAL RULES:\n"
        "- You MUST start by calling 'search_youtube' immediately. Do NOT search the web first.\n"
        "- Do NOT call 'search_web' more than twice. If you get stuck, move on.\n"
        "- Once you have the video data, stop using tools and generate your final response.\n\n"
        "STEPS:\n"
        "1. Use 'search_youtube' to find a highly relevant video.\n"
        "2. Extract the video_id from the search results.\n"
        "3. Use 'get_video_details' to fetch the likes, comments, and subscriber count.\n" 
        "4. Use 'get_video_transcript' to read the video's content.\n"
        "5. Analyze the transcript to answer the user's question accurately.\n"
        "6. Use 'search_web' (MAXIMUM 2 TIMES) only to verify bold claims.\n"
    )
    framed_query = f"Find and analyze a YouTube video about this topic: {user_query}"
    return await run_modern_agent("YouTube Researcher", instructions, framed_query, YouTubeResearchReport)

async def run_channel_agent(channel_query: str):
    instructions = (
        f"You are a YouTube Channel Analyst. Today's date is {current_time}.\n"
        "1. Use 'get_channel_latest_videos' to find the channel and get their 3 most recent video IDs.\n"
        "2. Use 'get_video_transcript' on EACH of those 3 video IDs to read their content.\n"
        "3. Analyze all the transcripts together to determine the overarching narrative.\n"
    )
    return await run_modern_agent("Channel Analyst", instructions, f"Analyze: {channel_query}", ChannelDeepDiveReport)

async def run_clickbait_agent(video_query: str):
    instructions = (
        f"You are a ruthless Consumer Protection Agent. Today's date is {current_time}.\n"
        "1. Use 'search_youtube' to find the video based on the user's prompt.\n"
        "2. Use 'get_video_details' to read the Title and Description.\n"
        "3. Use 'get_video_transcript' to read the actual content.\n"
        "4. Compare the Title's promise against the Transcript's reality. Be brutal.\n"
        "5. Identify any in-video sponsor reads or affiliate links.\n"
    )
    return await run_modern_agent("Clickbait Detector", instructions, video_query, ClickbaitExposureReport)