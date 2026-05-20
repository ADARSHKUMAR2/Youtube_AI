import os
from dotenv import load_dotenv
load_dotenv(override=True)
from mcp.server.fastmcp import FastMCP
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from pydantic import BaseModel, Field

# Initialize the MCP Server
mcp = FastMCP("YouTube-Agent-Server")

# Initialize YouTube API Client
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

class VideoResult(BaseModel):
    title: str = Field(description="The title of the YouTube video")
    video_id: str = Field(description="The unique YouTube video ID")
    url: str = Field(description="The full URL to the video")

@mcp.tool()
def search_youtube(query: str, max_results: int = 5) -> str:
    """Search YouTube for videos based on a query."""
    request = youtube.search().list(
        q=query,
        part='snippet',
        type='video',
        maxResults=max_results,
        order='date'
    )
    response = request.execute()
    
    results = []
    for item in response.get('items', []):
        video = VideoResult(
            title=item['snippet']['title'],
            video_id=item['id']['videoId'],
            url=f"https://www.youtube.com/watch?v={item['id']['videoId']}"
        )
        results.append(f"Title: {video.title} | URL: {video.url}")
    
    return "\n".join(results)

@mcp.tool()
def get_video_transcript(video_id: str) -> str:
    """Fetch the transcript/captions for a specific YouTube video ID."""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([t['text'] for t in transcript_list])
        return text[:5000] # Truncate to save token space
    except Exception as e:
        return f"Could not retrieve transcript: {str(e)}"

if __name__ == "__main__":
    # Run the MCP server over standard input/output (stdio)
    mcp.run()

