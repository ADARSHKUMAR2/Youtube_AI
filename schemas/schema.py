from pydantic import BaseModel, Field
from typing import Optional

# --- 1. Pydantic Schemas ---
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
        description="A 1-2 sentence summary of the audience's reaction based on the comments."
    )

class ChannelDeepDiveReport(BaseModel):
    channel_name: str = Field(description="The official name of the channel")
    overarching_theme: str = Field(description="A comprehensive summary of the channel's current focus, narrative, or bias based on their recent videos")
    recent_topics: list[str] = Field(description="A bulleted list of the specific topics covered in the analyzed videos")
    target_audience: str = Field(description="Who this channel appears to be creating content for")

class ClickbaitExposureReport(BaseModel):
    video_title: str = Field(description="The exact title of the video")
    the_promise: str = Field(description="What the title and thumbnail are promising the viewer (e.g., 'A $10k/month secret')")
    the_reality: str = Field(description="What the transcript actually delivers. Does it fulfill the promise, or is it fluff?")
    clickbait_score: int = Field(description="A score from 1 to 100. 1 = Completely honest, 100 = Absolute scam/clickbait.")
    sponsors_found: list[str] = Field(description="List of brands or products being shilled/sponsored in the video or description.")
    final_verdict: str = Field(description="A brutal, honest 1-sentence summary of whether the video is worth watching.")