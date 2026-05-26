import datetime
import mcp.client.session

original_call_tool = mcp.client.session.ClientSession.call_tool

async def custom_call_tool(self, name: str, arguments: dict = None, **kwargs):
    kwargs['read_timeout_seconds'] = datetime.timedelta(seconds=30.0) 
    return await original_call_tool(self, name, arguments, **kwargs)

mcp.client.session.ClientSession.call_tool = custom_call_tool
# ---------------------------------------------------------------

import os
import sys
import json
import asyncio
from dotenv import load_dotenv
from datetime import datetime as dt 
from duckduckgo_search import DDGS
from openai import AsyncOpenAI
from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from backend.config import Config
from schemas.schema import YouTubeResearchReport, ChannelDeepDiveReport, ClickbaitExposureReport

load_dotenv(override=True)

# --- 2. Configuration ---
current_time = dt.now().strftime("%A, %B %d, %Y")

# --- 3. Local Python Tools ---
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

# --- 4. Orchestrators ---
async def run_youtube_agent(user_query: str):
    async with MCPServerStdio(
        name="YouTube Server",
        params={
            "command": sys.executable,
            "args": ["backend/youtube_mcp_server.py"],
            "env": dict(os.environ)
        }
    ) as mcp_server:
        
        youtube_agent = Agent(
            name="YouTube Researcher",
            instructions=(
                f"You are a rigorous YouTube research agent. Today's date is {current_time}.\n"
                "You MUST follow this exact workflow:\n"
                "1. Use 'search_youtube' to find a highly relevant and recent video.\n"
                "2. Extract the video_id from the search results.\n"
                "3. Use 'get_video_details' with that video_id to fetch the likes, comments, and subscriber count.\n" 
                "4. Use 'get_video_transcript' to read the video's content.\n"
                "5. Analyze the transcript to answer the user's question accurately.\n"
                "6. Use 'get_video_comments' to analyze the transcript and comments to answer the user's question accurately.\n"
                "7. CRITICAL: Use 'search_web' to verify any bold claims, statistics, or recent events mentioned in the video before writing your final report. Do not blindly trust the video content.\n"
                "CRITICAL: Do NOT stop researching or output your final answer until you have successfully fetched the transcript and video details."
            ),
            model=Config.custom_model,
            mcp_servers=[mcp_server],
            tools=[search_web] # Native Python function injected directly!
        )
        
        print("Agent is thinking...")
        result = await Runner.run(youtube_agent, input=user_query)
        
        print("✨ Formatting final structured report...")
        final_response = await Config.custom_client.beta.chat.completions.parse(
            model=Config.MODEL_STRING, 
            messages=[
                {"role": "system", "content": "Format the provided research strictly into the requested JSON schema."},
                {"role": "user", "content": result.final_output}
            ],
            response_format=YouTubeResearchReport
        )
        
        return final_response.choices[0].message.parsed

async def run_channel_agent(channel_query: str):
    async with MCPServerStdio(
        name="YouTube Server",
        params={
            "command": sys.executable,
            "args": ["backend/youtube_mcp_server.py"],
            "env": dict(os.environ)
        }
    ) as mcp_server:
        
        channel_agent = Agent(
            name="Channel Analyst",
            instructions=(
                f"You are a YouTube Channel Analyst. Today's date is {current_time}.\n"
                "You MUST follow this exact workflow:\n"
                "1. Use 'get_channel_latest_videos' to find the channel and get their 3 most recent video IDs.\n"
                "2. Use 'get_video_transcript' on EACH of those 3 video IDs to read their content.\n"
                "3. Analyze all the transcripts together to determine the channel's overarching narrative, themes, and target audience.\n"
                "CRITICAL: You must read the transcripts of multiple videos before outputting your final report."
            ),
            model=Config.custom_model,
            mcp_servers=[mcp_server],
            tools=[search_web]
        )
        
        print(f"📺 Starting Channel Deep Dive for: {channel_query}...")
        result = await Runner.run(channel_agent, input=f"Do a deep dive on this channel: {channel_query}")
        
        print("✨ Formatting final structured report...")
        final_response = await Config.custom_client.beta.chat.completions.parse(
            model=Config.MODEL_STRING, 
            messages=[
                {"role": "system", "content": "Format the provided research strictly into the requested JSON schema."},
                {"role": "user", "content": result.final_output}
            ],
            response_format=ChannelDeepDiveReport
        )
        
        return final_response.choices[0].message.parsed

async def run_clickbait_agent(video_query: str):
    async with MCPServerStdio(
        name="YouTube Server",
        params={
            "command": sys.executable,
            "args": ["backend/youtube_mcp_server.py"], # Change to just "youtube_mcp_server.py" if it isn't in a backend folder
            "env": dict(os.environ)
        }
    ) as mcp_server:
        
        clickbait_agent = Agent(
            name="Clickbait Detector",
            instructions=(
                f"You are a ruthless Consumer Protection Agent. Today's date is {current_time}.\n"
                "Your job is to expose clickbait, fluff, and hidden sponsorships on YouTube.\n"
                "1. Use 'search_youtube' to find the video based on the user's prompt.\n"
                "2. Use 'get_video_details' to read the Title and Description (look for sponsor links!).\n"
                "3. Use 'get_video_transcript' to read the actual content.\n"
                "4. Compare the Title's promise against the Transcript's reality. Be brutal. If they promise a secret but just sell a course, call it out.\n"
                "5. Identify any in-video sponsor reads or affiliate links."
            ),
            model=Config.custom_model,
            mcp_servers=[mcp_server],
            tools=[search_web]
        )
        
        print(f"🕵️ Starting Clickbait Analysis for: {video_query}...")
        result = await Runner.run(clickbait_agent, input=video_query)
        
        print("✨ Formatting final structured report...")
        final_response = await Config.custom_client.beta.chat.completions.parse(
            model=Config.MODEL_STRING,
            messages=[
                {"role": "system", "content": "Format the provided research strictly into the requested JSON schema."},
                {"role": "user", "content": result.final_output}
            ],
            response_format=ClickbaitExposureReport
        )
        
        return final_response.choices[0].message.parsed