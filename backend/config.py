import os
from openai import AsyncOpenAI
from langsmith.wrappers import wrap_openai
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from google import genai
from agents.extensions.models.litellm_model import LitellmModel

class Config:
        """Builds and returns the configured GitHub/Azure model object."""
        
        openai_key=os.getenv("OPENAI_API_KEY")        
        openai_model="gpt-4o-mini"
        