from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.agentHandler import run_youtube_agent, run_channel_agent, run_clickbait_agent
from schemas.schema import YouTubeResearchReport, ChannelDeepDiveReport, ClickbaitExposureReport
import traceback
# 1. Initialize the FastAPI app
app = FastAPI(
    title="YouTube AI Agent API",
    description="API for analyzing YouTube videos and channels using MCP and LLMs."
)

# 2. Define the expected input schema from the frontend
class AgentRequest(BaseModel):
    query: str

# 3. Endpoint for Single Video Research
@app.post("/api/research/video", response_model=YouTubeResearchReport)
async def research_video(request: AgentRequest):
    try:
        print(f"API received video request: {request.query}")
        # Run the async agent natively
        report = await run_youtube_agent(request.query)
        return report
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# 4. Endpoint for Channel Deep Dive
@app.post("/api/research/channel", response_model=ChannelDeepDiveReport)
async def research_channel(request: AgentRequest):
    try:
        print(f"API received channel request: {request.query}")
        # Run the async agent natively
        report = await run_channel_agent(request.query)
        return report
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/research/clickbait", response_model=ClickbaitExposureReport)
async def research_clickbait(request: AgentRequest):
    try:
        print(f"API received clickbait request: {request.query}")
        report = await run_clickbait_agent(request.query)
        return report
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))