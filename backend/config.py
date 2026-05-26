import os
from openai import AsyncOpenAI
from langsmith.wrappers import wrap_openai
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

class Config:
        """Builds and returns the configured GitHub/Azure model object."""
        
        # 1. Build the explicit client
        custom_client = AsyncOpenAI(
            base_url="https://models.inference.ai.azure.com",
            api_key=os.environ.get("OPENAI_API_KEY") 
        )
        
        # 2. Wrap it with LangSmith
        tracked_client = wrap_openai(custom_client)

        MODEL_STRING = "gpt-4.1-nano" 
        # Wrap the client for the Agents SDK

        custom_model = OpenAIChatCompletionsModel(
            model=MODEL_STRING, 
            openai_client=custom_client
        )
        