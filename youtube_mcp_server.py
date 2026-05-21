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

@mcp.tool()
def get_video_details(video_id: str) -> str:
    """Fetch statistics for a video including likes, comments, and channel subscribers."""
    try:
        # 1. Get video stats and the channel ID
        video_req = youtube.videos().list(part='statistics,snippet', id=video_id)
        video_res = video_req.execute()
        
        if not video_res.get('items'):
            return "Video details not found."
            
        v_item = video_res['items'][0]
        likes = v_item['statistics'].get('likeCount', 'N/A')
        comments = v_item['statistics'].get('commentCount', 'N/A')
        channel_id = v_item['snippet']['channelId']
        
        # 2. Get channel stats to find subscriber count
        channel_req = youtube.channels().list(part='statistics', id=channel_id)
        channel_res = channel_req.execute()
        subs = channel_res['items'][0]['statistics'].get('subscriberCount', 'N/A')
        
        return f"Likes: {likes}, Comments: {comments}, Subscribers: {subs}"
    except Exception as e:
        return f"Failed to retrieve video details: {str(e)}"

@mcp.tool()
def get_video_comments(video_id: str, max_results: int = 20) -> str:
    """Fetch the top comments for a video to analyze audience sentiment."""
    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=max_results,
            order="relevance" # Gets the most upvoted/relevant comments first
        )
        response = request.execute()
        
        comments = []
        for item in response.get("items", []):
            text = item["snippet"]["topLevelComment"]["snippet"]["textOriginal"]
            # Clean up newlines to save tokens
            text = text.replace("\n", " ").strip()
            comments.append(f"- {text}")
            
        if not comments:
            return "No comments found or comments are disabled."
            
        return "\n".join(comments)
    except Exception as e:
        return f"Could not retrieve comments (they might be disabled): {str(e)}"

@mcp.tool()
def get_channel_latest_videos(channel_query: str, max_results: int = 3) -> str:
    """Search for a YouTube channel by name or handle and fetch their most recent video IDs."""
    try:
        # 1. Find the channel ID based on the query
        channel_req = youtube.search().list(
            q=channel_query,
            type='channel',
            part='snippet',
            maxResults=1
        )
        channel_res = channel_req.execute()
        
        if not channel_res.get('items'):
            return f"Could not find a channel matching '{channel_query}'."
            
        channel_id = channel_res['items'][0]['snippet']['channelId']
        channel_title = channel_res['items'][0]['snippet']['title']
        
        # 2. Get the latest videos from that specific channel
        vid_req = youtube.search().list(
            channelId=channel_id,
            type='video',
            part='snippet',
            order='date',
            maxResults=max_results
        )
        vid_res = vid_req.execute()
        
        results = [f"Found Channel: {channel_title} (ID: {channel_id})"]
        for item in vid_res.get('items', []):
            video_id = item['id']['videoId']
            title = item['snippet']['title']
            results.append(f"Title: {title} | Video ID: {video_id}")
            
        return "\n".join(results)
    except Exception as e:
        return f"Failed to retrieve channel videos: {str(e)}"
        
if __name__ == "__main__":
    # Run the MCP server over standard input/output (stdio)
    mcp.run()
