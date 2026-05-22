import os
from openai import AsyncOpenAI
from langsmith.wrappers import wrap_openai

def get_github_model():
    """Builds and returns the configured GitHub/Azure model object."""
    
    # 1. Build the explicit client
    custom_client = AsyncOpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=os.environ.get("OPENAI_API_KEY") 
    )
    
    # 2. Wrap it with LangSmith
    tracked_client = wrap_openai(custom_client)
    
    # 3. Return None as the first item so agent.py unpacks it correctly
    return tracked_client